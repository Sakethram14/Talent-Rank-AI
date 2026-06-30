import io
import csv
from typing import Sequence

class ExportService:
    def generate_hackathon_csv(self, candidate_ids: Sequence[str]) -> str:
        """
        Generates the official CSV string required for submission.
        Format: candidate_id, rank
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["candidate_id", "rank"])
        
        # Output exactly the top candidates provided, usually 100
        for rank, cid in enumerate(candidate_ids, start=1):
            writer.writerow([cid, rank])
            
        return output.getvalue()
