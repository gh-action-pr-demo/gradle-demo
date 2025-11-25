import _ from "lodash";

const payload = _.merge(
  { app: "demo-npm-app" },
  { timestamp: new Date().toISOString() }
);

console.log("Demo npm app payload:", payload);

