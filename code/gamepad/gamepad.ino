#include "USB.h"
#include "USBHIDKeyboard.h"
#include "Bounce2.h"

USBHIDKeyboard Keyboard;

// Game control buttons (9)
const byte gameButtonPins[9] = {1, 2, 3, 4, 5, 6, 7, 8, 9};
const byte gameKeyCodes[9] = {
  KEY_KP_7, KEY_KP_8, KEY_KP_9,  // Top row
  KEY_KP_4, KEY_KP_5, KEY_KP_6,  // Middle row
  KEY_KP_1, KEY_KP_2, KEY_KP_3   // Bottom row
};

// System control buttons (3)
const byte systemButtonPins[3] = {10, 11, 12};
const byte systemKeyCodes[3] = {
  KEY_RETURN,  // Menu/Start
  'l',       // Leaderboard
  KEY_ESC   // Escape
};

// Create bounce objects for all buttons
Bounce gameButtons[9];
Bounce systemButtons[3];

void setup() {
  // Initialize game buttons with pull-up resistors
  for(int i = 0; i < 9; i++) {
    pinMode(gameButtonPins[i], INPUT_PULLUP);
    gameButtons[i].attach(gameButtonPins[i]);
    gameButtons[i].interval(25); // 25ms debounce interval
  }
  
  // Initialize system buttons with pull-up resistors
  for(int i = 0; i < 3; i++) {
    pinMode(systemButtonPins[i], INPUT_PULLUP);
    systemButtons[i].attach(systemButtonPins[i]);
    systemButtons[i].interval(25); // 25ms debounce interval
  }
  
  // Initialize USB HID keyboard
  Keyboard.begin();
  USB.begin();
}

void loop() {
  // Update game button states
  for(int i = 0; i < 9; i++) {
    gameButtons[i].update();
    
    // Check if button was pressed
    if(gameButtons[i].fell()) {
      Keyboard.write(gameKeyCodes[i]);
    }
  }
  
  // Update system button states
  for(int i = 0; i < 3; i++) {
    systemButtons[i].update();
    
    // Check if button was pressed
    if(systemButtons[i].fell()) {
      Keyboard.write(systemKeyCodes[i]);
    }
  }
}