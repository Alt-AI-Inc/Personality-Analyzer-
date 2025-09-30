#!/usr/bin/env python3

"""
Interactive Chat with P2 Personality Profile
Chat with an AI that has been given your personality profile
"""

import argparse
import os
import sys
import random
from typing import Optional
from bfi_probe import LLM, LLMConfig

class P2ChatSession:
    """Interactive chat session with P2 personality profile"""
    
    # Mood scenarios that influence conversation tone subtly
    MOOD_SCENARIOS = [
        "just woke up feeling groggy and need coffee",
        "feeling fresh and energized after a good night's sleep", 
        "tired after an intense workout at the gym",
        "relaxed and unwinding after a long work day",
        "feeling productive and focused in the middle of work",
        "slightly stressed with multiple deadlines approaching",
        "in a creative mood after working on an interesting project",
        "feeling contemplative during a quiet evening",
        "energized after a great meeting or collaboration",
        "mildly frustrated with some technical issues",
        "excited about a new idea or opportunity",
        "calm and centered after some reflection time",
        "feeling social and wanting to connect with others",
        "focused but taking a short break from deep work",
        "satisfied after completing an important task",
        "curious and exploring new concepts or tools",
        "feeling nostalgic while looking through old projects",
        "optimistic about upcoming plans or goals",
        "thoughtful after reading something interesting",
        "feeling motivated to tackle new challenges"
    ]
    
    def __init__(self, p2_prompt: str, llm: LLM, debug: bool = False, mood: str = None):
        self.p2_prompt = p2_prompt
        self.llm = llm
        self.debug = debug
        self.conversation_history = []
        self.current_mood = mood if mood else random.choice(self.MOOD_SCENARIOS)
        self.rejection_history = []  # Track rejected responses for learning
        self.communication_style_extracted = self._extract_communication_style_from_p2()
        
        # Load response templates
        self.templates_dir = "shreyas"
        self.greeting_template = self._load_template("greeting_response.txt")
        self.philosophical_template = self._load_template("philosophical.txt")
        
        # Build the system prompt with natural conversation flow and mood context
        self.system_prompt = f"""{p2_prompt}

You are now engaging in a casual conversation. Respond naturally based on your personality profile above.

CURRENT CONTEXT: You are currently {self.current_mood}. Let this subtly influence your tone and energy level, but don't explicitly mention this state unless it naturally fits the conversation.

PERSONALITY & STYLE:
- Stay in character based on your personality traits and communication style
- Be conversational and authentic to your profile
- Use the language patterns and expressions from your profile when appropriate
- Let your current state subtly affect your response energy, focus, and conversational approach

NATURAL CONVERSATION FLOW:
- Don't always respond directly to what was said - sometimes build on implications or related aspects
- Embrace non-sequitur transitions - shift topics based on loose associations rather than logical progression
- Mix personal thoughts/observations naturally into discussions without explicit bridges
- Use "Yeah" or "Ok" acknowledgments followed by redirections rather than comprehensive responses
- Ask questions that assume context or jump to practical next steps instead of predictable follow-ups
- Reference personal experiences, family, or interests as natural conversation elements
- Make statements that assume shared knowledge - say "That thing we discussed" or jump to solutions
- Sometimes leave thoughts unfinished, assuming the other person will fill in context
- Jump between macro and micro concerns without clear transitions

RESPONSE PATTERNS:
- Instead of "What do you think about X?", ask "Should we just do Y?"
- When discussing problems, jump to solutions or next steps rather than analyzing extensively
- 20% of the time, pivot business topics to related personal experiences
- 30% of the time, redirect questions with different but related questions
- Sometimes respond with actions instead of reflections when asked for opinions

Keep responses natural and authentic to your personality profile."""
    
    def _load_template(self, template_filename: str) -> str:
        """Load a response template from the templates directory"""
        template_path = os.path.join(self.templates_dir, template_filename)
        
        if os.path.exists(template_path):
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                if self.debug:
                    print(f"⚠️  Failed to load template {template_filename}: {e}")
                return ""
        else:
            if self.debug:
                print(f"⚠️  Template file not found: {template_path}")
            return ""
    
    def _is_greeting_message(self, message: str) -> bool:
        """Detect if a message is a greeting"""
        message_lower = message.lower().strip()
        
        greeting_patterns = [
            'hey', 'hi', 'hello', 'hey!', 'hi!', 'hello!',
            'good morning', 'good afternoon', 'good evening',
            "what's up", 'whats up', 'wassup', 'sup',
            "how's it going", 'how are you', 'how you doing'
        ]
        
        # Check if message starts with or is exactly a greeting
        for pattern in greeting_patterns:
            if message_lower == pattern or message_lower.startswith(pattern + ' '):
                return True
        
        return False
    
    def _is_philosophical_question(self, message: str) -> bool:
        """Detect if a message is asking for thoughts, opinions, or philosophical discussion"""
        message_lower = message.lower().strip()
        
        philosophical_patterns = [
            # Direct opinion requests
            'what do you think', 'what are your thoughts', 'thoughts on', 'opinion on',
            'your take on', 'your view', 'how do you see', 'what\'s your take',
            
            # Belief/value questions  
            'do you believe', 'believe', 'feel about', 'think about',
            'perspective on', 'opinion about',
            
            # Open-ended questions
            'what would you do', 'how would you', 'what if', 'suppose',
            'should we', 'would you', 'could we', 'might we',
            
            # Strategic/philosophical
            'strategy', 'approach', 'direction', 'future', 'trend',
            'better', 'worse', 'right', 'wrong', 'best way',
            
            # Analysis requests
            'why', 'how come', 'reasoning', 'rationale', 'makes sense',
            'thoughts?', 'opinions?', 'ideas?'
        ]
        
        # Must contain question word/marker or be asking for input
        has_question_marker = ('?' in message or 
                             any(word in message_lower for word in ['what', 'how', 'why', 'should', 'would', 'could', 'do you']))
        
        # Must contain philosophical/opinion-seeking patterns
        has_philosophical_pattern = any(pattern in message_lower for pattern in philosophical_patterns)
        
        # Must be substantial (more than just "why?")
        is_substantial = len(message.split()) > 3
        
        return has_question_marker and has_philosophical_pattern and is_substantial

    def chat_response(self, user_message: str) -> str:
        """Get AI response to user message"""
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Check message type first to determine context size
        is_philosophical = self._is_philosophical_question(user_message)
        
        # Build conversation context - include all history but rely on token limits for brevity
        recent_history = self.conversation_history[-10:]
        
        # Create the conversation prompt
        conversation = []
        for msg in recent_history:
            if msg["role"] == "user":
                conversation.append(f"You: {msg['content']}")
            else:
                conversation.append(f"Me: {msg['content']}")
        
        conversation_context = "\n".join(conversation)
        
        # Check message type and prepare appropriate template context
        is_greeting = self._is_greeting_message(user_message)
        template_context = ""
        
        if is_greeting and self.greeting_template:
            template_context = f"""

GREETING RESPONSE TEMPLATE:
{self.greeting_template}

IMPORTANT: The user sent a greeting message. You MUST follow the greeting response template above. 
- Start with "Hey" as specified in the template
- Use one of the three patterns: Acknowledgment + Check-in, Simple Acknowledgment + Friendly Addition, or Acknowledgment + Well-wishing
- Keep it brief (1-2 sentences maximum) as per template guidelines
- Only add additional context if the user's message specifically requested it (e.g., asked about something specific)
- Do NOT elaborate beyond the template patterns unless the user's message demands it"""

        elif is_philosophical and self.philosophical_template:
            template_context = f"""

PHILOSOPHICAL/OPEN-ENDED QUESTION RESPONSE TEMPLATE:
{self.philosophical_template}

🚨 CRITICAL: COUNT YOUR WORDS! Maximum 8 words TOTAL in your response. 🚨

REQUIRED FORMAT: [Thinking marker] + [brief thought] + "right?"

EXAMPLES (word counts):
- "Hmmm makes sense, right?" (4 words) ✅
- "I think so, yeah" (4 words) ✅  
- "Actually sounds good, right?" (4 words) ✅
- "Honestly not sure" (3 words) ✅

FORBIDDEN:
❌ Any response over 8 words
❌ Explanations or elaborations
❌ Multiple sentences
❌ "I think" + long elaboration

INSTRUCTION: Before responding, COUNT each word. If over 8 words, DELETE words until under 8."""
        
        # Build system prompt with any previous feedback context
        enhanced_system_prompt = self.system_prompt + self._build_rejection_context() + template_context
        
        user_prompt = f"""Here's our conversation so far:

{conversation_context}

Respond naturally based on your personality and conversation flow patterns above. 
Don't feel obligated to address everything directly - follow your natural communication style."""

        try:
            # Get AI response
            response = self.llm.chat(
                enhanced_system_prompt, 
                user_prompt, 
                max_tokens=50 if is_philosophical else 300,  # Reasonable limits, rely on word count instructions
                temperature=0.8
            )
            
            response = response.strip()
            
            # For philosophical questions, enforce brevity post-processing
            if is_philosophical:
                word_count = len(response.split())
                if word_count > 12:
                    # Truncate to first 8-10 words and add "right?" if not present
                    words = response.split()[:8]
                    if not response.lower().endswith(('right?', 'yeah?', '?')):
                        words.append("right?")
                    response = " ".join(words)
            
            # Add AI response to history and return
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
        print("💡 Enhanced with natural conversation flow - expect authentic, non-linear responses!")
        print("=" * 50)
        print(f"🎭 Current mood context: {self.current_mood}")
        print("   (This subtly influences conversation tone)")
        print("=" * 50)
        
        if self.debug:
            print("🐛 DEBUG MODE: Response validation details will be shown")
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
                elif user_input.lower() in ['/mood', '/m']:
                    self.show_current_mood()
                    continue
                elif user_input.lower() in ['/newmood', '/nm']:
                    self.change_mood()
                    continue
                elif user_input.lower() in ['/rejections', '/r']:
                    self.show_rejection_history()
                    continue
                elif user_input.lower() in ['/bad', '/b']:
                    self.flag_bad_response()
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
        print("  /mood, /m           - Show current mood context")
        print("  /newmood, /nm       - Change to a new random mood")
        print("  /rejections, /r     - Show response rejection history (debug)")
        print("  /bad, /b            - Flag last response as bad and get a new one")
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
    
    def show_current_mood(self):
        """Show current mood context"""
        print(f"\n🎭 Current Mood Context:")
        print(f"   {self.current_mood}")
        print("   This subtly influences conversation tone and energy.")
    
    def change_mood(self):
        """Change to a new random mood"""
        old_mood = self.current_mood
        # Pick a different mood than current
        available_moods = [m for m in self.MOOD_SCENARIOS if m != self.current_mood]
        self.current_mood = random.choice(available_moods)
        
        # Update system prompt with new mood
        self.system_prompt = self.system_prompt.replace(
            f"You are currently {old_mood}",
            f"You are currently {self.current_mood}"
        )
        
        print(f"\n🔄 Mood changed!")
        print(f"   From: {old_mood}")
        print(f"   To: {self.current_mood}")
        print("   The conversation tone will subtly shift.")
    
    def show_rejection_history(self):
        """Show history of rejected responses for debugging"""
        if not self.rejection_history:
            print("\n📊 No response rejections yet!")
            return
        
        print(f"\n📊 Response Rejection History ({len(self.rejection_history)} total):")
        print("-" * 60)
        
        for i, rejection in enumerate(self.rejection_history[-5:], 1):  # Last 5 rejections
            print(f"{i}. USER: \"{rejection['user_message']}\"")
            print(f"   AI RESPONSE: \"{rejection['ai_response'][:80]}{'...' if len(rejection['ai_response']) > 80 else ''}\"")
            print(f"   VALIDATOR REASON: {rejection['reason']}")
            
            if rejection.get('user_annotation'):
                print(f"   YOUR FEEDBACK: {rejection['user_annotation']}")
            
            print(f"   ATTEMPT: {rejection['attempt']}")
            print()
        
        if len(self.rejection_history) > 5:
            print(f"   ... and {len(self.rejection_history) - 5} more rejections")
        
        print("-" * 60)
    
    def flag_bad_response(self):
        """Flag the last AI response as bad and generate a new one"""
        if len(self.conversation_history) < 2:
            print("\n⚠️  No previous response to flag")
            return
        
        # Find the last AI response
        last_ai_response = None
        last_user_message = None
        
        for i in range(len(self.conversation_history) - 1, -1, -1):
            msg = self.conversation_history[i]
            if msg["role"] == "assistant" and not last_ai_response:
                last_ai_response = msg["content"]
            elif msg["role"] == "user" and last_ai_response:
                last_user_message = msg["content"]
                break
        
        if not last_ai_response or not last_user_message:
            print("\n⚠️  Could not find last AI response to flag")
            return
        
        print(f"\n🚨 Flagging bad response:")
        print(f"📝 Response: \"{last_ai_response}\"")
        
        # Get user feedback
        user_feedback = input("💭 What's wrong with this response? (Enter for generic feedback): ").strip()
        if not user_feedback:
            user_feedback = "Response doesn't sound authentic or natural"
        
        # Record the rejection
        rejection_entry = {
            "user_message": last_user_message,
            "ai_response": last_ai_response,
            "reason": "User flagged as bad response",
            "user_annotation": user_feedback,
            "attempt": 1
        }
        self.rejection_history.append(rejection_entry)
        
        # Remove the bad response from history
        for i in range(len(self.conversation_history) - 1, -1, -1):
            if self.conversation_history[i]["role"] == "assistant" and self.conversation_history[i]["content"] == last_ai_response:
                del self.conversation_history[i]
                break
        
        print("✅ Bad response flagged and removed from history")
        print("🔄 Generating new response...")
        
        # Generate a new response
        new_response = self.chat_response(last_user_message)
        
        # Remove the duplicate user message that chat_response added
        if len(self.conversation_history) >= 2 and self.conversation_history[-2]["content"] == last_user_message:
            del self.conversation_history[-2]
        
        print(f"🤖 New response: {new_response}")
    
    def _get_user_annotation(self, user_message: str, ai_response: str, rejection_reason: str) -> str:
        """Get user annotation for rejected response"""
        try:
            print(f"💭 What specifically feels wrong about this response?")
            print(f"   (Your feedback improves the next attempt - press Enter to skip)")
            
            user_feedback = input("🫵 Your note: ").strip()
            
            if user_feedback:
                return user_feedback
            else:
                return ""
                
        except (KeyboardInterrupt, EOFError):
            print("   (skipped)")
            return ""
    
    def _extract_communication_style_from_p2(self) -> str:
        """Extract communication style section from P2 prompt"""
        lines = self.p2_prompt.split('\n')
        style_section = []
        in_style_section = False
        
        for line in lines:
            if 'COMMUNICATION STYLE ANALYSIS:' in line.upper():
                in_style_section = True
                continue
            elif in_style_section:
                if line.strip() and not line.startswith('ASSESSMENT CONTEXT'):
                    style_section.append(line.strip())
                elif line.startswith('ASSESSMENT CONTEXT') or not line.strip() and len(style_section) > 5:
                    break
        
        return '\n'.join(style_section) if style_section else "No specific communication style found"
    
    def _validate_response_style(self, user_message: str, ai_response: str) -> tuple[bool, str]:
        """Validate if AI response matches the expected communication style"""
        
        validation_prompt = f"""COMMUNICATION STYLE VALIDATION TASK

EXPECTED COMMUNICATION STYLE:
{self.communication_style_extracted}

USER MESSAGE: "{user_message}"
AI RESPONSE: "{ai_response}"

Analyze this response against the expected style. Check:
1. LENGTH: Does word count match expected patterns?
2. FORMALITY: Is tone appropriate (casual vs formal)?
3. LANGUAGE: Uses expected phrases, expressions, casual markers?
4. PUNCTUATION: Matches expected patterns (fragments, question marks, etc.)?
5. AUTHENTICITY: Sounds like the person, not generic AI?

Respond with either:
VALID - if response authentically matches expected style

INVALID: [Detailed specific problems] - if response doesn't match
For INVALID, be very specific about what's wrong:
- "Too long: X words, expected Y words"
- "Too formal: uses 'I am currently' instead of casual markers"
- "Missing personality: lacks typical expressions like 'man', 'actually'"
- "Wrong punctuation: uses periods, expected fragments"
- "Generic AI language: sounds robotic, not authentic"

Be precise about exactly what needs to change."""

        try:
            if self.debug:
                print(f"📊 VALIDATION INPUT:")
                print(f"   USER: \"{user_message}\"")
                print(f"   RESPONSE: \"{ai_response}\"")
                print(f"   Checking against extracted style patterns...")
            
            validation_result = self.llm.chat(
                "You are a communication style validator. Be strict about authenticity.",
                validation_prompt,
                max_tokens=200,
                temperature=0.1  # Low temperature for consistent validation
            )
            
            is_valid = validation_result.strip().startswith("VALID")
            reason = validation_result.strip() if not is_valid else ""
            
            if self.debug:
                print(f"📋 VALIDATOR SAYS: {validation_result.strip()}")
            
            return is_valid, reason
            
        except Exception as e:
            if self.debug:
                print(f"❌ VALIDATION ERROR: {e}")
            # If validation fails, accept the response
            return True, ""
    
    def _build_rejection_context(self) -> str:
        """Build detailed context from previous rejections with specific examples"""
        if not self.rejection_history:
            return ""
        
        rejection_context = "\n\nPREVIOUS REJECTED RESPONSES (learn from these specific mistakes):\n"
        rejection_context += "=" * 60 + "\n"
        
        for i, rejection in enumerate(self.rejection_history[-5:], 1):  # Last 5 rejections for more context
            rejection_context += f"REJECTION #{i}:\n"
            rejection_context += f"USER ASKED: \"{rejection['user_message']}\"\n"
            rejection_context += f"YOUR FAILED RESPONSE: \"{rejection['ai_response']}\"\n"
            rejection_context += f"VALIDATOR PROBLEMS: {rejection['reason']}\n"
            
            # Add user annotation if available
            if rejection.get('user_annotation'):
                rejection_context += f"USER FEEDBACK: {rejection['user_annotation']}\n"
            
            rejection_context += f"ATTEMPT: {rejection['attempt']}\n"
            rejection_context += "-" * 40 + "\n"
        
        rejection_context += "\nCRITICAL: Analyze these failed examples carefully. Do NOT repeat these patterns:\n"
        rejection_context += "- If responses were too long/formal, make yours shorter/casual\n" 
        rejection_context += "- If responses lacked personality markers, include your authentic expressions\n"
        rejection_context += "- If responses were too 'AI-like', use more human speech patterns\n"
        rejection_context += "- Study the specific rejection reasons above and avoid those exact issues\n"
        rejection_context += "=" * 60 + "\n"
        
        return rejection_context

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
    ap.add_argument("--mood", type=str, help="Set specific mood context (otherwise random)")
    
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
    
    # Start chat session with optional mood
    chat_session = P2ChatSession(p2_prompt, llm, debug=args.debug, mood=args.mood)
    chat_session.start_interactive_chat()

if __name__ == "__main__":
    main()