import threading, time
from plugins.proactive_plugin import ProactivePlugin
from openai_gateway import PromptService


class ProactiveScheduler:
    def __init__(self, preprompt: str, prompt_name: str):
        self.invocation_dict = dict()
        self.pending_events = []
        self.llm_service = PromptService(prompt_name='default', preprompt=preprompt)

    def trigger_pending(self):
        while len(self.pending_events) > 0:
            self.trigger(self.pending_events.pop(0))

    def trigger(self, event: str):
        for plugin in self.invocation_dict.get(event, []):
            additional_context = plugin.invoke(event)
            if additional_context is not None:
                if type(additional_context) is str:
                    self.llm_service.add_context(role="user", content=f"Context: {additional_context}")
                else:
                    self.llm_service.context.append(additional_context)

    def register_plugin(self, plugin: ProactivePlugin, event: str):
        if event in self.invocation_dict:
            self.invocation_dict[event].append(plugin)
        else:
            self.invocation_dict[event] = [plugin]

    def start_timer(self,
                    interval_secs: int,
                    event_name: str,
                    invoke_immediately: bool = False):
        Timer(interval_secs, event_name, self).start_timer(invoke_immediately)

    def invoke_llm(self, custom_prompt = None):
        result = self.llm_service.invoke_llm(custom_prompt)
        self.llm_service.add_context(role="assistant", content=result)
        return result

class Timer:
    def __init__(self,
                 interval_secs: int,
                 event_name: str,
                 scheduler: ProactiveScheduler):
        self.next_time = time.time()
        self.interval_secs = interval_secs
        self.event_name = event_name
        self.scheduler = scheduler

    def start_timer(self, invoke_immediately: bool):
        def timer_event():
            self.next_time += self.interval_secs
            threading.Timer(self.next_time - time.time(), timer_event).start()
            self.scheduler.pending_events.append(self.event_name)
        if invoke_immediately:
            threading.Thread(target=timer_event).start()
        else:
            self.next_time = time.time() + self.interval_secs
            threading.Timer(self.next_time - time.time(), timer_event).start()
