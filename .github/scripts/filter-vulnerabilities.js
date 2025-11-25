#!/usr/bin/env node

/**
 * Filter vulnerabilities from dependency-review-action output
 * 
 * This script:
 * 1. Fetches policy files from upstream (GitHub repo or local)
 * 2. Parses vulnerable-changes JSON from dependency-review-action
 * 3. Filters to only include packages in policy files
 * 4. Filters to only include critical severity (configurable)
 * 5. Outputs filtered results and metrics
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// Configuration
const policyPathEnv = process.env.POLICY_PATH || '.github/policies';
const localPolicyEnv = process.env.LOCAL_POLICY_DIR || policyPathEnv;
const resolvedLocalPolicyDir = path.isAbsolute(localPolicyEnv)
        ? localPolicyEnv
        : path.resolve(process.cwd(), localPolicyEnv);

const CONFIG = {
        policySource: process.env.POLICY_SOURCE || 'local', // 'local' or 'github'
        policyRepo: process.env.POLICY_REPO || '', // e.g., 'your-org/dependency-policies'
        policyPath: policyPathEnv, // path in repo
        policyRef: process.env.POLICY_REF || 'main',
        minSeverity: process.env.MIN_SEVERITY || 'critical', // critical, high, moderate, low
        localPolicyDir: resolvedLocalPolicyDir,
};

// Severity levels (higher number = more severe)
const SEVERITY_LEVELS = {
        critical: 4,
        high: 3,
        moderate: 2,
        low: 1,
};

/**
 * Fetch policy file from GitHub
 */
async function fetchPolicyFromGitHub(ecosystem) {
        return new Promise((resolve, reject) => {
                const url = `https://raw.githubusercontent.com/${CONFIG.policyRepo}/${CONFIG.policyRef}/${CONFIG.policyPath}/${ecosystem}.txt`;

                https.get(url, (res) => {
                        let data = '';

                        if (res.statusCode !== 200) {
                                console.error(`Failed to fetch ${ecosystem}.txt from GitHub: ${res.statusCode}`);
                                resolve([]);
                                return;
                        }

                        res.on('data', (chunk) => { data += chunk; });
                        res.on('end', () => {
                                const packages = data.split('\n')
                                        .map(line => line.trim())
                                        .filter(line => line && !line.startsWith('#'));
                                resolve(packages);
                        });
                }).on('error', (err) => {
                        console.error(`Error fetching ${ecosystem}.txt:`, err.message);
                        resolve([]);
                });
        });
}

/**
 * Load policy file from local filesystem
 */
function loadPolicyFromLocal(ecosystem) {
        const filePath = path.join(CONFIG.localPolicyDir, `${ecosystem}.txt`);

        if (!fs.existsSync(filePath)) {
                console.error(`Policy file not found: ${filePath}`);
                return [];
        }

        const content = fs.readFileSync(filePath, 'utf-8');
        return content.split('\n')
                .map(line => line.trim())
                .filter(line => line && !line.startsWith('#'));
}

/**
 * Discover available policy files
 * For local: scan directory for .txt files
 * For GitHub: try common ecosystems + config-defined ones
 */
async function discoverEcosystems() {
        if (CONFIG.policySource === 'github') {
                // For GitHub, try common ecosystems + any custom ones from config
                const commonEcosystems = ['maven', 'npm', 'pip', 'go', 'gradle', 'cargo', 'composer', 'nuget', 'rubygems'];
                const ecosystems = [];

                // Test each ecosystem to see if file exists
                for (const ecosystem of commonEcosystems) {
                        const url = `https://raw.githubusercontent.com/${CONFIG.policyRepo}/${CONFIG.policyRef}/${CONFIG.policyPath}/${ecosystem}.txt`;
                        try {
                                const response = await new Promise((resolve) => {
                                        https.get(url, (res) => {
                                                resolve(res.statusCode === 200);
                                        }).on('error', () => resolve(false));
                                });
                                if (response) {
                                        ecosystems.push(ecosystem);
                                }
                        } catch (err) {
                                // Ignore errors, just skip this ecosystem
                        }
                }

                console.error(`Discovered ${ecosystems.length} ecosystem policy files from GitHub`);
                return ecosystems;
        } else {
                // For local, scan directory for .txt files
                if (!fs.existsSync(CONFIG.localPolicyDir)) {
                        console.error(`Policy directory not found: ${CONFIG.localPolicyDir}`);
                        return [];
                }

                const files = fs.readdirSync(CONFIG.localPolicyDir);
                const ecosystems = files
                        .filter(file => file.endsWith('.txt') && file !== 'config.txt')
                        .map(file => file.replace('.txt', ''));

                console.error(`Discovered ${ecosystems.length} ecosystem policy files from local directory: ${ecosystems.join(', ')}`);
                return ecosystems;
        }
}

/**
 * Load all policy files (dynamically discovered)
 */
async function loadPolicies() {
        const ecosystems = await discoverEcosystems();
        const policies = {};

        for (const ecosystem of ecosystems) {
                if (CONFIG.policySource === 'github') {
                        policies[ecosystem] = await fetchPolicyFromGitHub(ecosystem);
                } else {
                        policies[ecosystem] = loadPolicyFromLocal(ecosystem);
                }
                console.error(`Loaded ${policies[ecosystem].length} packages for ${ecosystem}`);
        }

        return policies;
}

/**
 * Check if package matches policy
 */
function matchesPolicy(packageName, policyPackages) {
        return policyPackages.some(policyPkg => {
                // Exact match
                if (packageName === policyPkg) return true;

                // For Maven: match group:artifact (ignore version)
                if (packageName.includes(':') && policyPkg.includes(':')) {
                        const pkgParts = packageName.split(':');
                        const policyParts = policyPkg.split(':');
                        return pkgParts[0] === policyParts[0] && pkgParts[1] === policyParts[1];
                }

                return false;
        });
}

/**
 * Check if severity meets minimum threshold
 */
function meetsSeverityThreshold(severity) {
        const vulnLevel = SEVERITY_LEVELS[severity?.toLowerCase()] || 0;
        const minLevel = SEVERITY_LEVELS[CONFIG.minSeverity.toLowerCase()] || 0;
        return vulnLevel >= minLevel;
}

/**
 * Filter vulnerabilities based on policy and severity
 */
function filterVulnerabilities(vulnerableChanges, policies) {
        const filtered = [];
        const metrics = {};

        for (const change of vulnerableChanges) {
                const ecosystem = change.ecosystem?.toLowerCase();
                const packageName = change.name;

                // Check if package is in policy
                if (!ecosystem || !policies[ecosystem]) {
                        continue;
                }

                if (!matchesPolicy(packageName, policies[ecosystem])) {
                        continue;
                }

                // Filter vulnerabilities by severity
                const filteredVulns = (change.vulnerabilities || []).filter(vuln =>
                        meetsSeverityThreshold(vuln.severity)
                );

                if (filteredVulns.length === 0) {
                        continue;
                }

                // Add to filtered results
                const filteredChange = {
                        ...change,
                        vulnerabilities: filteredVulns,
                };
                filtered.push(filteredChange);

                // Track metrics
                if (!metrics[packageName]) {
                        metrics[packageName] = {
                                ecosystem,
                                status: 'unfixed',
                                current_version: change.version,
                                vulnerability_count: filteredVulns.length,
                                max_severity: filteredVulns.reduce((max, v) => {
                                        const level = SEVERITY_LEVELS[v.severity?.toLowerCase()] || 0;
                                        const maxLevel = SEVERITY_LEVELS[max?.toLowerCase()] || 0;
                                        return level > maxLevel ? v.severity : max;
                                }, 'low'),
                        };
                }
        }

        return { filtered, metrics };
}

/**
 * Main function
 */
async function main() {
        try {
                console.error('=== Policy Filter Configuration ===');
                console.error(`Source           : ${CONFIG.policySource}`);
                if (CONFIG.policySource === 'github') {
                        console.error(`Repo/Ref/Path    : ${CONFIG.policyRepo} @ ${CONFIG.policyRef} (${CONFIG.policyPath})`);
                } else {
                        console.error(`Local Directory   : ${CONFIG.localPolicyDir}`);
                }
                console.error(`Min Severity      : ${CONFIG.minSeverity}`);
                console.error('===================================');

                // Load policies
                console.error('Loading policies...');
                const policies = await loadPolicies();

                // Read vulnerable-changes from environment or stdin
                let vulnerableChanges;
                if (process.env.VULNERABLE_CHANGES) {
                        vulnerableChanges = JSON.parse(process.env.VULNERABLE_CHANGES);
                } else {
                        const stdin = fs.readFileSync(0, 'utf-8');
                        vulnerableChanges = JSON.parse(stdin);
                }

                console.error(`Processing ${vulnerableChanges.length} vulnerable changes...`);

                // Filter vulnerabilities
                const { filtered, metrics } = filterVulnerabilities(vulnerableChanges, policies);

                console.error(`Filtered to ${filtered.length} policy violations`);

                // Output results
                const output = {
                        filtered_vulnerabilities: filtered,
                        metrics,
                        summary: {
                                total_vulnerabilities: vulnerableChanges.length,
                                policy_violations: filtered.length,
                                min_severity: CONFIG.minSeverity,
                        },
                };

                console.log(JSON.stringify(output, null, 2));

                // Exit with error code if violations found
                process.exit(filtered.length > 0 ? 1 : 0);

        } catch (error) {
                console.error('Error:', error.message);
                console.error(error.stack);
                process.exit(2);
        }
}

// Run if called directly
if (require.main === module) {
        main();
}

module.exports = { loadPolicies, filterVulnerabilities, matchesPolicy };
