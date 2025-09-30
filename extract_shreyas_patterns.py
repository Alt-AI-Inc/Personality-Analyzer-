#!/usr/bin/env python3

"""
Extract Common Response Patterns from Shreyas's Messages
Analyze actual messages to find the most common words, phrases, and response structures
"""

import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

def extract_shreyas_messages(file_path: str) -> List[Dict]:
    """Extract all messages sent by Shreyas Srinivasan"""
    shreyas_messages = []
    
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # WhatsApp pattern: [YYYY/MM/DD, HH:MM:SS] Name: Message
    pattern = r'\[(\d{4}/\d{1,2}/\d{1,2}),?\s+(\d{1,2}:\d{2}:\d{2})\]\s+([^:]+?):\s+(.*?)(?=\n\[\d{4}/|$)'
    matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
    
    for match in matches:
        date_str, time_str, sender, message = match
        message = message.strip().replace('\n', ' ')
        
        # Only include Shreyas's messages
        if 'Shreyas Srinivasan' in sender and message and not message.startswith(('‎', '<Media omitted>')):
            shreyas_messages.append({
                'date': date_str,
                'time': time_str,
                'message': message
            })
    
    print(f"📱 Found {len(shreyas_messages)} messages from Shreyas Srinivasan")
    return shreyas_messages

def analyze_common_patterns(messages: List[Dict]) -> Dict:
    """Analyze common patterns in Shreyas's messages"""
    
    all_messages = [msg['message'] for msg in messages]
    
    # 1. Most common starting words/phrases
    starting_words = []
    starting_phrases = []
    
    for msg in all_messages:
        words = msg.split()
        if words:
            starting_words.append(words[0].lower())
            if len(words) > 1:
                starting_phrases.append(f"{words[0]} {words[1]}".lower())
    
    common_starters = Counter(starting_words).most_common(20)
    common_phrase_starters = Counter(starting_phrases).most_common(20)
    
    # 2. Most common individual words (excluding very common ones)
    all_words = []
    skip_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their', 'there', 'where', 'when', 'why', 'how', 'what', 'who', 'which', 'i', 'you', 'he', 'she', 'we', 'me', 'him', 'her', 'us'}
    
    for msg in all_messages:
        words = re.findall(r'\b\w+\b', msg.lower())
        for word in words:
            if len(word) > 2 and word not in skip_words:
                all_words.append(word)
    
    common_words = Counter(all_words).most_common(30)
    
    # 3. Most common 2-word and 3-word phrases
    two_word_phrases = []
    three_word_phrases = []
    
    for msg in all_messages:
        words = msg.lower().split()
        for i in range(len(words) - 1):
            two_word_phrases.append(f"{words[i]} {words[i+1]}")
            if i < len(words) - 2:
                three_word_phrases.append(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    common_2word = Counter(two_word_phrases).most_common(25)
    common_3word = Counter(three_word_phrases).most_common(20)
    
    # 4. Punctuation patterns
    punctuation_patterns = {
        'ends_with_period': sum(1 for msg in all_messages if msg.endswith('.')),
        'ends_with_question': sum(1 for msg in all_messages if msg.endswith('?')),
        'ends_with_exclamation': sum(1 for msg in all_messages if msg.endswith('!')),
        'no_ending_punctuation': sum(1 for msg in all_messages if not msg.endswith(('.', '?', '!'))),
        'contains_comma': sum(1 for msg in all_messages if ',' in msg),
        'total_messages': len(all_messages)
    }
    
    # 5. Message length patterns
    word_counts = [len(msg.split()) for msg in all_messages]
    
    # 6. Find messages with specific thinking/response words
    thinking_words = ['hmmm', 'hmm', 'think', 'actually', 'honestly', 'makes', 'sense', 'yeah', 'ok', 'sure', 'cool']
    thinking_patterns = {}
    
    for word in thinking_words:
        messages_with_word = [msg for msg in all_messages if word.lower() in msg.lower()]
        thinking_patterns[word] = {
            'count': len(messages_with_word),
            'percentage': round(len(messages_with_word) / len(all_messages) * 100, 1),
            'examples': messages_with_word[:5]  # First 5 examples
        }
    
    return {
        'total_messages': len(all_messages),
        'common_starters': common_starters,
        'common_phrase_starters': common_phrase_starters,
        'common_words': common_words,
        'common_2word_phrases': common_2word,
        'common_3word_phrases': common_3word,
        'punctuation_patterns': punctuation_patterns,
        'avg_word_count': sum(word_counts) / len(word_counts),
        'word_count_distribution': {
            '1_word': sum(1 for c in word_counts if c == 1),
            '2_3_words': sum(1 for c in word_counts if 2 <= c <= 3),
            '4_10_words': sum(1 for c in word_counts if 4 <= c <= 10),
            '11_plus_words': sum(1 for c in word_counts if c > 10)
        },
        'thinking_patterns': thinking_patterns
    }

def find_pattern_examples(messages: List[Dict], pattern_word: str, context_needed: int = 2) -> List[Dict]:
    """Find examples of messages containing specific patterns with context"""
    examples = []
    
    for i, msg in enumerate(messages):
        if pattern_word.lower() in msg['message'].lower():
            example = {
                'message': msg['message'],
                'date': msg['date'],
                'context_before': [],
                'context_after': []
            }
            
            # Add context if available (previous and next messages from conversation)
            if i > 0:
                example['context_before'] = [messages[max(0, i-context_needed):i]]
            if i < len(messages) - 1:
                example['context_after'] = [messages[i+1:min(len(messages), i+context_needed+1)]]
            
            examples.append(example)
    
    return examples[:10]  # Return first 10 examples

def main():
    file_path = "Data/Abhishek.txt"
    
    print("🔍 Extracting Common Response Patterns from Shreyas's Messages")
    print("=" * 70)
    
    # Extract all of Shreyas's messages
    messages = extract_shreyas_messages(file_path)
    
    if not messages:
        print("❌ No messages found from Shreyas Srinivasan")
        return
    
    # Analyze patterns
    patterns = analyze_common_patterns(messages)
    
    # Display results
    print(f"\n📊 ANALYSIS RESULTS ({patterns['total_messages']} messages)")
    print("=" * 70)
    
    print(f"\n🎯 TOP 10 MOST COMMON STARTING WORDS:")
    for word, count in patterns['common_starters'][:10]:
        percentage = round(count / patterns['total_messages'] * 100, 1)
        print(f"   {word}: {count} times ({percentage}%)")
    
    print(f"\n💭 TOP 10 MOST COMMON STARTING PHRASES:")
    for phrase, count in patterns['common_phrase_starters'][:10]:
        percentage = round(count / patterns['total_messages'] * 100, 1)
        print(f"   '{phrase}': {count} times ({percentage}%)")
    
    print(f"\n📝 TOP 15 MOST COMMON WORDS:")
    for word, count in patterns['common_words'][:15]:
        percentage = round(count / (patterns['total_messages'] * patterns['avg_word_count']) * 100, 2)
        print(f"   {word}: {count} times")
    
    print(f"\n🔗 TOP 10 MOST COMMON 2-WORD PHRASES:")
    for phrase, count in patterns['common_2word_phrases'][:10]:
        print(f"   '{phrase}': {count} times")
    
    print(f"\n📏 MESSAGE LENGTH PATTERNS:")
    dist = patterns['word_count_distribution']
    total = patterns['total_messages']
    print(f"   1 word: {dist['1_word']} ({round(dist['1_word']/total*100, 1)}%)")
    print(f"   2-3 words: {dist['2_3_words']} ({round(dist['2_3_words']/total*100, 1)}%)")
    print(f"   4-10 words: {dist['4_10_words']} ({round(dist['4_10_words']/total*100, 1)}%)")
    print(f"   11+ words: {dist['11_plus_words']} ({round(dist['11_plus_words']/total*100, 1)}%)")
    print(f"   Average: {round(patterns['avg_word_count'], 1)} words per message")
    
    print(f"\n⭐ THINKING/RESPONSE WORD ANALYSIS:")
    for word, data in patterns['thinking_patterns'].items():
        if data['count'] > 10:  # Only show words used more than 10 times
            print(f"   '{word}': {data['count']} times ({data['percentage']}%)")
            print(f"      Examples: {data['examples'][:2]}")
            print()

if __name__ == "__main__":
    main()