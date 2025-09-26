#!/usr/bin/env python3

"""
Interactive Chat with P2 Personality Profile
Chat with an AI that has been given your personality profile
"""

import argparse
import os
import sys
from typing import Optional
from bfi_probe import LLM, LLMConfig

class P2ChatSession:
    """Interactive chat session with P2 personality profile"""
    
    def __init__(self, p2_prompt: str, llm: LLM, debug: bool = False):
        self.p2_prompt = p2_prompt
        self.llm = llm
        self.debug = debug
        self.conversation_history = []
        
        # Build the system prompt
        self.system_prompt = f"""{p2_prompt}

You are now engaging in a casual conversation. Respond naturally based on your personality profile above.
- Stay in character based on your personality traits and communication style
- Be conversational and authentic to your profile
- Keep responses reasonably brief (1-3 sentences unless asked for more detail)
- Use the language patterns and expressions from your profile when appropriate"""

    def chat_response(self, user_message: str) -> str:
        """Get AI response to user message"""
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Build conversation context (last 10 messages to keep it manageable)
        recent_history = self.conversation_history[-10:]
        
        # Create the conversation prompt
        conversation = []
        for msg in recent_history:
            if msg["role"] == "user":
                conversation.append(f"You: {msg['content']}")
            else:
                conversation.append(f"Me: {msg['content']}")
        
        conversation_context = "\n".join(conversation)
        
        user_prompt = f"""Here's our conversation so far:

{conversation_context}

Respond to the latest message naturally, staying true to your personality profile."""

        try:
            # Get AI response with reasonable token limit
            response = self.llm.chat(
                self.system_prompt, 
                user_prompt, 
                max_tokens=300,
                temperature=0.8  # Slightly more creative for conversation
            )
            
            # Add AI response to history
            self.conversation_history.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            return f"[ERROR: {e}]"
    
    def start_interactive_chat(self):
        """Start the interactive chat loop"""
        print("🤖 P2 Personality Chat Session")
        print("=" * 50)
        print("Type your messages and press Enter.")
        print("Commands: '/help' for help, '/quit' to exit, '/history' to see conversation")
        print("=" * 50)
        
        # Show a brief personality summary if debug mode
        if self.debug:
            print("\n[DEBUG] Personality Profile Preview:")
            print(self.p2_prompt[:300] + "..." if len(self.p2_prompt) > 300 else self.p2_prompt)
            print("-" * 50)
        
        print("\n💬 Chat started! Say hello or ask me anything...")
        
        while True:
            try:
                # Get user input
                user_input = input("\n🫵 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['/quit', '/exit', '/q']:
                    print("\n👋 Chat ended. Goodbye!")
                    break
                elif user_input.lower() in ['/help', '/h']:
                    self.show_help()
                    continue
                elif user_input.lower() in ['/history', '/hist']:
                    self.show_history()
                    continue
                elif user_input.lower() in ['/personality', '/p2']:
                    self.show_personality_summary()
                    continue
                elif user_input.lower() in ['/clear', '/reset']:
                    self.conversation_history = []
                    print("🧹 Conversation history cleared!")
                    continue
                
                # Get AI response
                print("🤖 Me: ", end="", flush=True)
                response = self.chat_response(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
    
    def show_help(self):
        """Show help commands"""
        print("\n📋 Available Commands:")
        print("  /quit, /exit, /q    - End the chat session")
        print("  /help, /h           - Show this help")
        print("  /history, /hist     - Show conversation history")  
        print("  /personality, /p2   - Show personality profile summary")
        print("  /clear, /reset      - Clear conversation history")
        print("  Just type normally  - Chat with the AI")
    
    def show_history(self):
        """Show conversation history"""
        if not self.conversation_history:
            print("\n📝 No conversation history yet.")
            return
        
        print(f"\n📝 Conversation History ({len(self.conversation_history)} messages):")
        print("-" * 30)
        for i, msg in enumerate(self.conversation_history, 1):
            role_icon = "🫵" if msg["role"] == "user" else "🤖"
            role_name = "You" if msg["role"] == "user" else "Me"
            print(f"{i:2d}. {role_icon} {role_name}: {msg['content']}")
        print("-" * 30)
    
    def show_personality_summary(self):
        """Show a summary of the personality profile"""
        print("\n🧬 Personality Profile Summary:")
        print("-" * 40)
        
        # Extract key sections from P2 prompt
        lines = self.p2_prompt.split('\n')
        in_traits_section = False
        traits_found = 0
        
        for line in lines:
            line = line.strip()
            if 'BIG FIVE TRAITS' in line.upper():
                in_traits_section = True
                print("Big Five Traits:")
                continue
            elif in_traits_section and line.startswith(('O:', 'C:', 'E:', 'A:', 'N:')):
                print(f"  {line}")
                traits_found += 1
                if traits_found >= 5:
                    break
        
        print("-" * 40)

def load_p2_profile(file_path: str) -> Optional[str]:
    """Load P2 profile from file"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"❌ Error loading P2 profile: {e}")
        return None

def list_available_p2_files(directory: str = "results") -> list:
    """List available P2 profile files"""
    if not os.path.exists(directory):
        return []
    
    p2_files = []
    for filename in os.listdir(directory):
        if filename.endswith('_p2.txt') or 'p2_prompt' in filename:
            p2_files.append(os.path.join(directory, filename))
    
    return sorted(p2_files)

def main():
    ap = argparse.ArgumentParser(description="Interactive Chat with P2 Personality Profile")
    ap.add_argument("--p2-file", type=str, help="Path to P2 personality profile file")
    ap.add_argument("--model", type=str, default="gpt-4o-mini", 
                   choices=["gpt-4o-mini", "gpt-4o", "gpt-5"])
    ap.add_argument("--debug", action="store_true", help="Enable debug output")
    ap.add_argument("--list-p2", action="store_true", help="List available P2 files and exit")
    
    args = ap.parse_args()
    
    # List available P2 files if requested
    if args.list_p2:
        print("📁 Available P2 Profile Files:")
        p2_files = list_available_p2_files()
        if not p2_files:
            print("   No P2 files found in results/ directory")
            print("   Run a personality assessment first to generate P2 profiles")
        else:
            for i, file_path in enumerate(p2_files, 1):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                print(f"   {i}. {filename} ({file_size} bytes)")
                print(f"      Path: {file_path}")
        return
    
    # Handle P2 file selection
    if not args.p2_file:
        # Try to find P2 files automatically
        p2_files = list_available_p2_files()
        if not p2_files:
            print("❌ No P2 files found!")
            print("   Run --list-p2 to see available files")
            print("   Or specify a file with --p2-file <path>")
            return
        elif len(p2_files) == 1:
            args.p2_file = p2_files[0]
            print(f"🎯 Auto-selected: {os.path.basename(args.p2_file)}")
        else:
            print("🤔 Multiple P2 files found. Please select one:")
            for i, file_path in enumerate(p2_files, 1):
                filename = os.path.basename(file_path)
                print(f"   {i}. {filename}")
            
            try:
                selection = int(input("\nEnter number (1-{}): ".format(len(p2_files))))
                if 1 <= selection <= len(p2_files):
                    args.p2_file = p2_files[selection - 1]
                    print(f"✅ Selected: {os.path.basename(args.p2_file)}")
                else:
                    print("❌ Invalid selection")
                    return
            except (ValueError, KeyboardInterrupt):
                print("\n❌ Invalid input or cancelled")
                return
    
    # Load P2 profile
    p2_prompt = load_p2_profile(args.p2_file)
    if not p2_prompt:
        print(f"❌ Could not load P2 profile from: {args.p2_file}")
        return
    
    print(f"✅ Loaded P2 profile: {os.path.basename(args.p2_file)} ({len(p2_prompt)} chars)")
    
    # Initialize LLM
    cfg = LLMConfig(model=args.model, temperature=0.8, max_tokens=300)
    llm = LLM(cfg, debug=args.debug)
    
    # Start chat session
    chat_session = P2ChatSession(p2_prompt, llm, debug=args.debug)
    chat_session.start_interactive_chat()

if __name__ == "__main__":
    main()