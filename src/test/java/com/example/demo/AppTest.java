package com.example.demo;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class AppTest {
    @Test
    void testGetGreeting() {
        App app = new App();
        assertNotNull(app.getGreeting());
        assertEquals("Hello World!", app.getGreeting());
    }
}
