#!/usr/bin/env python3

"""
Interactive Chat with P2 Personality Profile
Chat with an AI that has been given your personality profile
"""

import argparse
import os
import sys
import random
import json
from typing import Optional, List, Dict, Tuple
from bfi_probe import LLM, LLMConfig
import tiktoken  # For accurate token counting

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
    
    def __init__(self, p2_prompt: str, llm: LLM, debug: bool = False, mood: str = None, chat_characteristics_path: str = "chat_characteristics.json", scenario: str = None, person_name: str = None):
        self.p2_prompt = p2_prompt
        self.llm = llm
        self.debug = debug
        self.conversation_history = []
        self.current_mood = mood if mood else random.choice(self.MOOD_SCENARIOS)
        self.rejection_history = []  # Track rejected responses for learning
        self.chat_characteristics_path = chat_characteristics_path
        self.scenario = scenario
        self.person_name = person_name if person_name else self._extract_person_name_from_p2()
        self.communication_style_extracted = self._extract_communication_style_from_p2()
        
        # Load response templates and characteristics
        self.templates_dir = "shreyas"
        self.greeting_template = self._load_template("greeting_response.txt")
        self.philosophical_template = self._load_template("philosophical.txt")
        self.chat_characteristics = self._load_chat_characteristics()
        
        # Context management settings from characteristics file
        self.tokenizer = tiktoken.get_encoding("cl100k_base")  # GPT-4 tokenizer
        settings = self.chat_characteristics.get("settings", {})
        self.max_context_tokens = settings.get("max_context_tokens", 32000)
        self.template_reinforcement_interval = settings.get("template_reinforcement_interval", 3000)
        self.max_tokens_philosophical = settings.get("max_tokens_philosophical", 50)
        self.max_tokens_general = settings.get("max_tokens_general", 300)
        self.max_tokens_initial = settings.get("max_tokens_initial", 100)
        self.temperature = settings.get("temperature", 0.2)
        self.last_reinforcement_tokens = 0
        self.template_adherence_scores = []  # Track performance over time
        
        # Build the system prompt with characteristics from JSON file
        general_conversation = self.chat_characteristics.get("general_conversation", {})
        conversation_prompt = general_conversation.get("system_prompt", "")

        # Build scenario context if provided
        scenario_context = ""
        if self.scenario:
            scenario_context = f"\n\nCONVERSATION SCENARIO: {self.scenario}\nYou are {self.person_name} in this scenario. Respond naturally based on this context and your personality."

        self.system_prompt = f"""{p2_prompt}

CURRENT CONTEXT: You are currently {self.current_mood}. Let this subtly influence your tone and energy level, but don't explicitly mention this state unless it naturally fits the conversation.{scenario_context}

{conversation_prompt}"""
    
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
    
    def _load_chat_characteristics(self) -> Dict:
        """Load chat characteristics from JSON file"""
        if os.path.exists(self.chat_characteristics_path):
            try:
                with open(self.chat_characteristics_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                if self.debug:
                    print(f"⚠️  Failed to load chat characteristics from {self.chat_characteristics_path}: {e}")
                return {}
        else:
            if self.debug:
                print(f"⚠️  Chat characteristics file not found: {self.chat_characteristics_path}")
            return {}
    
    def send_initial_message(self) -> str:
        """Generate and send an initial message to start the conversation"""
        initial_config = self.chat_characteristics.get("initial_message", {})

        if not initial_config.get("enabled", True):
            return None

        instructions = initial_config.get("instructions", "")
        examples = initial_config.get("examples", [])

        # Build initial message prompt
        scenario_context = ""
        if self.scenario:
            scenario_context = f"\n\nSCENARIO CONTEXT: {self.scenario}\nGenerate an opening message appropriate for this scenario."

        examples_text = ""
        if examples:
            examples_text = "\n\nEXAMPLES:\n" + "\n".join(f"- {ex}" for ex in examples)

        user_prompt = f"""Generate a natural opening message to start this conversation.

{instructions}{scenario_context}{examples_text}

IMPORTANT:
- Do NOT include your name in the message
- Just provide the greeting/opening message text directly
- Keep it brief (1-2 sentences), authentic to your personality, and natural."""

        try:
            response = self.llm.chat(
                self.system_prompt,
                user_prompt,
                max_tokens=self.max_tokens_initial,
                temperature=self.temperature
            )

            response = response.strip()

            # Clean up response if it includes the person's name at the start
            # Pattern: "Name: message" -> "message"
            if response.startswith(f"{self.person_name}:"):
                response = response[len(f"{self.person_name}:"):].strip()

            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            if self.debug:
                print(f"❌ Error generating initial message: {e}")
            return None

    def _is_greeting_message(self, message: str) -> bool:
        """Detect if a message is a greeting"""
        message_lower = message.lower().strip()
        
        detection_patterns = self.chat_characteristics.get("detection_patterns", {})
        greeting_patterns = detection_patterns.get("greeting_patterns", [])
        
        # Check if message starts with or is exactly a greeting
        for pattern in greeting_patterns:
            if message_lower == pattern or message_lower.startswith(pattern + ' '):
                return True
        
        return False
    
    def _is_philosophical_question(self, message: str) -> bool:
        """Detect if a message is asking for thoughts, opinions, or philosophical discussion"""
        message_lower = message.lower().strip()
        
        detection_patterns = self.chat_characteristics.get("detection_patterns", {})
        philosophical_patterns = detection_patterns.get("philosophical_patterns", [])
        
        # Must contain question word/marker or be asking for input
        has_question_marker = ('?' in message or 
                             any(word in message_lower for word in ['what', 'how', 'why', 'should', 'would', 'could', 'do you']))
        
        # Must contain philosophical/opinion-seeking patterns
        has_philosophical_pattern = any(pattern in message_lower for pattern in philosophical_patterns)
        
        # Must be substantial (more than just "why?")
        is_substantial = len(message.split()) > 3
        
        return has_question_marker and has_philosophical_pattern and is_substantial

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using GPT-4 tokenizer"""
        return len(self.tokenizer.encode(text))
    
    def _count_conversation_tokens(self) -> int:
        """Count total tokens in current conversation history"""
        total_tokens = 0
        for message in self.conversation_history:
            total_tokens += self._count_tokens(message["content"])
        return total_tokens
    
    def _needs_template_reinforcement(self, is_philosophical: bool) -> bool:
        """Check if we need to reinforce template instructions based on token count"""
        if not is_philosophical:
            return False
            
        current_tokens = self._count_conversation_tokens()
        tokens_since_last = current_tokens - self.last_reinforcement_tokens
        
        return tokens_since_last >= self.template_reinforcement_interval
    
    def _create_template_reinforcement(self, template_context: str) -> str:
        """Create a reinforcement message to maintain instruction adherence"""
        reinforcement_config = self.chat_characteristics.get("template_reinforcement", {})
        header = reinforcement_config.get("header", "").format(template_context=template_context)
        examples = reinforcement_config.get("examples", [])
        constraint = reinforcement_config.get("global_constraint", "")
        
        examples_text = "\nExamples: " + ", ".join(examples) if examples else ""
        
        return f"{header}{examples_text}\n{constraint}"
    
    def _compress_context_intelligently(self, messages: List[Dict], is_philosophical: bool) -> List[Dict]:
        """Compress conversation history while preserving template-relevant information"""
        if len(messages) <= 6:  # Keep recent messages as-is
            return messages
            
        # Always preserve system-level instructions and recent exchanges
        recent_messages = messages[-5:]  # Last 5 messages
        older_messages = messages[:-5]
        
        if is_philosophical:
            # For philosophical questions, compress more aggressively but preserve template patterns
            template_keywords = ['right?', 'hmmm', 'i think', 'makes sense', 'actually', 'honestly']
            
            preserved_messages = []
            for msg in older_messages:
                content_lower = msg["content"].lower()
                
                # Preserve messages that demonstrate good template adherence
                if any(keyword in content_lower for keyword in template_keywords):
                    preserved_messages.append(msg)
                elif len(msg["content"].split()) <= 12:  # Keep brief responses
                    preserved_messages.append(msg)
                # Compress longer messages to summaries
                elif msg["role"] == "user":
                    preserved_messages.append(msg)  # Keep user messages
                else:
                    # Summarize long AI responses
                    summary = f"[Responded briefly with thinking marker]"
                    preserved_messages.append({"role": "assistant", "content": summary})
            
            return preserved_messages + recent_messages
        else:
            # Standard compression for non-philosophical conversations
            return older_messages[-3:] + recent_messages  # Keep last 8 messages total

    def _compress_assistant_response(self, response: str, is_philosophical_context: bool) -> str:
        """Compress assistant responses to prevent verbosity reinforcement in conversation history"""
        word_count = len(response.split())
        
        if not is_philosophical_context or word_count <= 12:
            # Keep short responses as-is
            return response
        
        # For verbose philosophical responses, extract key components
        response_lower = response.lower()
        
        # Extract thinking marker
        thinking_markers = ['hmmm', 'i think', 'actually', 'honestly', 'makes sense', 'yeah', 'ok', 'sure', 'cool', 'got it']
        thinking_marker = None
        for marker in thinking_markers:
            if marker in response_lower:
                thinking_marker = marker.capitalize()
                break
        
        # Check if it has question ending
        has_question = response.rstrip().endswith('?') or 'right?' in response_lower
        
        # Extract core topic/subject (first few meaningful words after thinking marker)
        words = response.split()
        core_words = []
        skip_words = {'i', 'think', 'we', 'should', 'can', 'will', 'would', 'could', 'the', 'a', 'an', 'is', 'are', 'that', 'this'}
        
        for word in words[1:6]:  # Look at words after thinking marker
            if word.lower().rstrip('.,?!') not in skip_words and len(word) > 2:
                core_words.append(word.rstrip('.,?!'))
                if len(core_words) >= 2:  # Get 2-3 key words
                    break
        
        # Reconstruct compressed response
        if thinking_marker and core_words:
            if has_question:
                compressed = f"{thinking_marker}, {' '.join(core_words)}, right?"
            else:
                compressed = f"{thinking_marker}, {' '.join(core_words)}"
        else:
            # Fallback: use first 8 words
            compressed = ' '.join(words[:8])
            if not compressed.rstrip().endswith('?') and has_question:
                compressed += ", right?"
        
        return compressed

    def _score_template_adherence(self, response: str) -> float:
        """Score how well a response adheres to the philosophical template (0-3 scale)"""
        score = 0.0
        response_lower = response.lower()
        word_count = len(response.split())
        
        # Check for thinking markers (1 point)
        thinking_markers = ['hmmm', 'i think', 'actually', 'honestly', 'makes sense', 'yeah', 'ok', 'sure', 'cool', 'got it']
        if any(marker in response_lower for marker in thinking_markers):
            score += 1.0
        
        # Check for question patterns (1 point) 
        question_patterns = ['right?', 'yeah?', '?']
        if any(pattern in response_lower for pattern in question_patterns):
            score += 1.0
        
        # Check for brevity (1 point) - 12 words or less as per Shreyas style
        if word_count <= 12:
            score += 1.0
        elif word_count <= 15:
            score += 0.5  # Partial credit for somewhat brief
        
        return score

    def get_adherence_stats(self) -> Dict:
        """Get template adherence statistics for monitoring"""
        if not self.template_adherence_scores:
            return {"avg_score": 0, "total_responses": 0, "recent_trend": "N/A"}
        
        recent_scores = self.template_adherence_scores[-10:]  # Last 10 responses
        early_scores = self.template_adherence_scores[:10] if len(self.template_adherence_scores) >= 10 else self.template_adherence_scores
        
        avg_recent = sum(recent_scores) / len(recent_scores)
        avg_early = sum(early_scores) / len(early_scores)
        trend = "improving" if avg_recent > avg_early else "declining" if avg_recent < avg_early else "stable"
        
        return {
            "avg_score": sum(self.template_adherence_scores) / len(self.template_adherence_scores),
            "recent_avg": avg_recent,
            "total_responses": len(self.template_adherence_scores),
            "trend": trend,
            "current_tokens": self._count_conversation_tokens()
        }

    def chat_response(self, user_message: str) -> str:
        """Get AI response to user message with intelligent context management"""
        
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Check message type first to determine context size
        is_philosophical = self._is_philosophical_question(user_message)
        
        # Intelligent context management based on token count and conversation length
        current_tokens = self._count_conversation_tokens()
        
        if current_tokens > self.max_context_tokens:
            # Apply intelligent compression
            managed_history = self._compress_context_intelligently(self.conversation_history, is_philosophical)
        else:
            # Use standard windowing for shorter conversations
            managed_history = self.conversation_history[-10:]
        
        # Create the conversation prompt from managed history with response compression
        conversation = []
        for msg in managed_history:
            if msg["role"] == "user":
                conversation.append(f"You: {msg['content']}")
            else:
                # Compress assistant responses to prevent verbosity reinforcement
                compressed_response = self._compress_assistant_response(msg['content'], is_philosophical)
                conversation.append(f"{self.person_name}: {compressed_response}")
        
        conversation_context = "\n".join(conversation)
        
        # Check message type and prepare appropriate template context
        is_greeting = self._is_greeting_message(user_message)
        template_context = ""
        
        if is_greeting and self.greeting_template:
            greeting_config = self.chat_characteristics.get("greeting_response", {})
            header = greeting_config.get("template_header", "").format(greeting_template=self.greeting_template)
            instructions = greeting_config.get("instructions", [])
            
            instructions_text = "\n".join(f"- {instruction}" for instruction in instructions)
            template_context = f"{header}\n{instructions_text}"

        elif is_philosophical and self.philosophical_template:
            phil_config = self.chat_characteristics.get("philosophical_response", {})
            header = phil_config.get("template_header", "").format(philosophical_template=self.philosophical_template)
            override_instructions = phil_config.get("override_instructions", [])
            mandatory_rules = phil_config.get("mandatory_rules", {})
            forbidden = phil_config.get("forbidden", [])
            final_instruction = phil_config.get("final_instruction", "")
            
            override_text = "\n".join(f"- {instruction}" for instruction in override_instructions)
            brevity_rule = mandatory_rules.get("brevity_rule", "")
            format_rule = mandatory_rules.get("format", "")
            examples = mandatory_rules.get("examples", [])
            
            examples_text = "\nEXAMPLES (word counts):\n" + "\n".join(f"- {example}" for example in examples)
            forbidden_text = "\nFORBIDDEN FOR PHILOSOPHICAL QUESTIONS:\n" + "\n".join(f"❌ {item}" for item in forbidden)
            
            base_template = f"{header}\n{override_text}\n\nMANDATORY BREVITY RULE: {brevity_rule}\n\nREQUIRED FORMAT: {format_rule}{examples_text}{forbidden_text}\n\nINSTRUCTION: {final_instruction}"
            
            # Check if we need template reinforcement
            if self._needs_template_reinforcement(is_philosophical):
                template_context = self._create_template_reinforcement(base_template)
                self.last_reinforcement_tokens = current_tokens
                if self.debug:
                    print(f"🔄 Template reinforcement activated at {current_tokens} tokens")
            else:
                template_context = base_template
        
        # Build system prompt with any previous feedback context
        enhanced_system_prompt = self.system_prompt + self._build_rejection_context() + template_context
        
        user_prompt = f"""Here's our conversation so far:

{conversation_context}

Respond based on your personality and conversation flow patterns above. 
Don't feel obligated to address everything directly - follow your natural communication style."""

        try:
            # Get AI response
            response = self.llm.chat(
                enhanced_system_prompt, 
                user_prompt, 
                max_tokens=self.max_tokens_philosophical if is_philosophical else self.max_tokens_general,
                temperature=self.temperature
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
            
            # Monitor template adherence for philosophical responses
            if is_philosophical:
                adherence_score = self._score_template_adherence(response)
                self.template_adherence_scores.append(adherence_score)
                
                if self.debug:
                    print(f"📊 Template adherence score: {adherence_score:.2f}/3.0")
                    print(f"📈 Average over last 10: {sum(self.template_adherence_scores[-10:]) / min(len(self.template_adherence_scores), 10):.2f}")
            
            # Add AI response to history and return
            self.conversation_history.append({"role": "assistant", "content": response})
            return response
            
        except Exception as e:
            return f"[ERROR: {e}]"
    
    def start_interactive_chat(self):
        """Start the interactive chat loop"""
        print(f"🤖 P2 Personality Chat Session - Chatting with {self.person_name}")
        print("=" * 50)
        print("Type your messages and press Enter.")
        print("Commands: '/help' for help, '/quit' to exit, '/history' to see conversation")
        print("=" * 50)
        print("💡 Enhanced with natural conversation flow - expect authentic, non-linear responses!")
        print("=" * 50)
        if self.scenario:
            print(f"📝 Scenario: {self.scenario}")
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

        # Send initial message if enabled
        initial_message = self.send_initial_message()
        if initial_message:
            print(f"\n🤖 {self.person_name}: {initial_message}")
        else:
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
                elif user_input.lower() in ['/scenario', '/s']:
                    self.show_scenario()
                    continue
                elif user_input.lower() in ['/rejections', '/r']:
                    self.show_rejection_history()
                    continue
                elif user_input.lower() in ['/bad', '/b']:
                    self.flag_bad_response()
                    continue
                
                # Get AI response
                print(f"🤖 {self.person_name}: ", end="", flush=True)
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
        print("  /scenario, /s       - Show current scenario context")
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
            role_name = "You" if msg["role"] == "user" else self.person_name
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

    def show_scenario(self):
        """Show current scenario context"""
        if self.scenario:
            print(f"\n📝 Conversation Scenario:")
            print("-" * 60)
            print(f"{self.scenario}")
            print("-" * 60)
            print(f"You are talking to {self.person_name} in this context.")
        else:
            print("\n📝 No scenario set for this conversation.")
            print("   Use --scenario 'text' or --scenario-file 'path/to/file.txt' when starting the chat.")
    
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

        print(f"🤖 {self.person_name}: {new_response}")
    
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
    
    def _extract_person_name_from_p2(self) -> str:
        """Extract person name from P2 prompt"""
        lines = self.p2_prompt.split('\n')

        # Look for patterns like "You are [Name]" or mentions of a name
        for line in lines[:10]:  # Check first 10 lines
            if 'you are' in line.lower():
                # Extract name after "you are"
                parts = line.lower().split('you are')
                if len(parts) > 1:
                    name_part = parts[1].strip().rstrip('.,!')
                    # Get first word which is likely the name
                    name = name_part.split()[0] if name_part.split() else None
                    if name and name not in ['a', 'an', 'the']:
                        return name.capitalize()

        # Fallback: Look for capitalized words that might be names
        for line in lines[:5]:
            words = line.split()
            for word in words:
                if word[0].isupper() and len(word) > 2 and word.isalpha():
                    # Skip common words
                    if word.lower() not in ['the', 'you', 'are', 'this', 'profile', 'personality', 'assessment', 'big', 'five']:
                        return word

        return "the AI"

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

def load_scenario_from_file(file_path: str) -> Optional[str]:
    """Load scenario from text file"""
    if not os.path.exists(file_path):
        print(f"❌ Scenario file not found: {file_path}")
        return None

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        return content
    except Exception as e:
        print(f"❌ Error loading scenario file: {e}")
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
    ap.add_argument("--chat-characteristics", type=str, default="chat_characteristics.json",
                   help="Path to chat characteristics JSON file (default: chat_characteristics.json)")
    ap.add_argument("--scenario", type=str, help="Conversation scenario context as string (e.g., 'catching up over coffee')")
    ap.add_argument("--scenario-file", type=str, help="Path to text file containing scenario context (overrides --scenario)")
    ap.add_argument("--name", type=str, help="Person name (auto-extracted from P2 profile if not provided)")

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

    # Handle scenario loading (file takes precedence over string)
    scenario = None
    if args.scenario_file:
        scenario = load_scenario_from_file(args.scenario_file)
        if scenario:
            print(f"✅ Loaded scenario from file: {os.path.basename(args.scenario_file)} ({len(scenario)} chars)")
        else:
            print("⚠️  Failed to load scenario file, continuing without scenario")
    elif args.scenario:
        scenario = args.scenario
        print(f"✅ Using scenario: {scenario[:60]}{'...' if len(scenario) > 60 else ''}")

    # Initialize LLM
    cfg = LLMConfig(model=args.model, temperature=0.8, max_tokens=300)
    llm = LLM(cfg, debug=args.debug)

    # Start chat session with optional mood, scenario, and name
    chat_session = P2ChatSession(
        p2_prompt,
        llm,
        debug=args.debug,
        mood=args.mood,
        chat_characteristics_path=args.chat_characteristics,
        scenario=scenario,
        person_name=args.name
    )
    chat_session.start_interactive_chat()

if __name__ == "__main__":
    main()