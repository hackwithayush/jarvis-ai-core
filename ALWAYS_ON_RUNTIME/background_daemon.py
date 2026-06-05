"""
Background Daemon
The main 'Always-On' thread that coordinates states, voice, and autonomy.
"""
import time
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.absolute()))
from ALWAYS_ON_RUNTIME.active_task_queue import ActiveTaskQueue, TaskState
from ALWAYS_ON_RUNTIME.autonomous_dispatcher import AutonomousDispatcher
from ALWAYS_ON_RUNTIME.idle_monitor import IdleMonitor

try:
    from VOICE.wake_word.porcupine_engine import PorcupineEngine
except ImportError:
    PorcupineEngine = None

from VOICE.microphone.audio_input import AudioInput
from VOICE.speech_to_text.faster_whisper_engine import FasterWhisperEngine
from VOICE.text_to_speech.piper_engine import PiperEngine
from VOICE.audio_output.speaker import Speaker
from core.jarvis_brain import JarvisBrain

class BackgroundDaemon:
    def __init__(self):
        print("\n=======================================================")
        print("          JARVIS ALWAYS-ON RUNTIME BOOTING             ")
        print("=======================================================\n")
        
        self.queue = ActiveTaskQueue()
        self.wake_word = PorcupineEngine() if PorcupineEngine else None
        self.mic = AudioInput()
        self.stt = FasterWhisperEngine(model_size="base")
        self.tts = PiperEngine()
        self.speaker = Speaker()
        self.brain = JarvisBrain()
        self.dispatcher = AutonomousDispatcher(self.queue, self.brain)
        
        # Start Idle Monitor
        self.idle_monitor = IdleMonitor(self.queue)
        self.idle_monitor.start()
        
    def run(self):
        self.queue.set_state(TaskState.IDLE)
        
        while True:
            try:
                # Idle State: Waiting for Wake Word
                if self.wake_word and self.wake_word.wait_for_wake_word():
                    self.queue.set_state(TaskState.LISTENING)
                    
                    # Record Command
                    audio_file = self.mic.record_audio()
                    if not audio_file:
                        self.queue.set_state(TaskState.IDLE)
                        continue
                        
                    # Speech to Text
                    text_input = self.stt.transcribe(audio_file)
                    print(f"\n[DAEMON] Transcribed: '{text_input}'")
                    
                    if not text_input or len(text_input.strip()) < 2:
                        self.queue.set_state(TaskState.IDLE)
                        continue
                        
                    # Dispatch to Planner / Router
                    response_text = self.dispatcher.dispatch(text_input)
                    
                    # Speak output
                    self.queue.set_state(TaskState.SPEAKING)
                    output_file = self.tts.speak(response_text)
                    if output_file:
                        self.speaker.play_audio(output_file)
                    else:
                        print(f"[JARVIS SPEAKS]: {response_text}")
                        
                    self.queue.set_state(TaskState.IDLE)
                    
            except KeyboardInterrupt:
                print("\n[DAEMON] Shutting down...")
                break
            except Exception as e:
                self.queue.set_state(TaskState.ERROR)
                print(f"\n[DAEMON ERROR] {e}")
                time.sleep(2)
                self.queue.set_state(TaskState.IDLE)
