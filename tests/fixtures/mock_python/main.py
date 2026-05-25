from utils import compute_score

class ProcessManager:
    def __init__(self):
        self.score = 0

    def run_process(self, data):
        self.score = compute_score(data)
        return self.score
