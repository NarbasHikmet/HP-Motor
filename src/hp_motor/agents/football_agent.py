# HP Motor v5.0 - Copilot Agent Logic
from github_copilot import CopilotClient

class HPAgent:
    """HP Motor'un 'Düşünen' katmanı için Copilot SDK entegrasyonu."""
    def __init__(self, api_key):
        self.client = CopilotClient(api_key=api_key)

    def analyze_match_context(self, match_data):
        # Ajan, veriye bakıp 'Pep' veya 'Klopp' gibi yorum yapacak
        prompt = f"Şu maç verisini bir futbol analisti gibi yorumla: {match_data}"
        response = self.client.chat.complete(messages=[{"role": "user", "content": prompt}])
        return response.content
