#!/usr/bin/env python3

import re

def parse_whatsapp_export(file_path: str):
    """Parse WhatsApp export file - test version"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Test different patterns
    patterns = [
        r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.*?)(?=\n\[\d{4}/|$)',
        r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+):\s+(.*?)(?=\[\d|$)',
        r'\[([^]]+)\]\s+([^:]+):\s+(.*?)(?=\[[^]]+\]|$)'
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n=== PATTERN {i} ===")
        matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
        print(f"Found {len(matches)} matches")
        
        if matches:
            # Show first 5 matches
            for j, match in enumerate(matches[:5]):
                print(f"Match {j+1}: {match}")
            
            # Show unique senders
            if len(match) >= 3:  # At least timestamp and sender
                senders = set(match[-2] if len(match) == 4 else match[1] for match in matches)
                print(f"Senders: {sorted(senders)}")

if __name__ == "__main__":
    parse_whatsapp_export("Data/Abhishek.txt")