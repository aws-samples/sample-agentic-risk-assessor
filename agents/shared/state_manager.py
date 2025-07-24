class StateManager:
    def __init__(self, config):
        self.config = config
    
    async def initialize(self):
        pass
    
    async def save_state(self, state):
        pass
    
    async def load_state(self):
        return {}