#!/usr/bin/env python3
import os
import pygame
import sys

pygame.init()
os.makedirs('docs/sprites', exist_ok=True)

def save_sprite(surface, filename):
    filepath = f'docs/sprites/{filename}'
    pygame.image.save(surface, filepath)
    print(f"Saved: {filepath}")

def export_all_sprites():
    from main import Sprites
    
    # Create sprite generator instance
    sprites = Sprites()
    size = (80, 80)  # Standard sprite size
    
    print("Exporting sprites...")
    
    # Enemies
    save_sprite(sprites.hacker(size, 0), 'hacker1.png')
    save_sprite(sprites.hacker(size, 1), 'hacker2.png')
    save_sprite(sprites.hacker(size, 2), 'hacker3.png')
    save_sprite(sprites.boss(size), 'boss.png')
    save_sprite(sprites.apt(size), 'apt.png')
    save_sprite(sprites.social_engineer(size), 'social_engineer.png')
    save_sprite(sprites.phishing(size), 'phishing.png')
    
    # Friendlies
    save_sprite(sprites.shield(size), 'shield.png')
    save_sprite(sprites.it_admin(size), 'it_admin.png')
    save_sprite(sprites.lock(size), 'lock.png')
    
    # Power-ups (adjust method names as needed)
    save_sprite(sprites.pu_freeze(size), 'powerup_freeze.png')
    save_sprite(sprites.pu_time(size), 'powerup_time.png')
    save_sprite(sprites.pu_double(size), 'powerup_double.png')
    save_sprite(sprites.pu_slow(size), 'powerup_slow.png')
    
    print(f"\nDone! Check docs/sprites/")

if __name__ == '__main__':
    export_all_sprites()
    pygame.quit()