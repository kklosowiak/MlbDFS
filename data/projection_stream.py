import pandas as pd
import os
from config import config

class ProjectionStream:
    def __init__(self):
        self.projections_file = os.path.join(config.DATA_DIR, "base_projections.csv")
        
    def load_projections(self):
        """Loads the base projections for the current slate."""
        if not os.path.exists(self.projections_file):
            print(f"INFO: No base projections found at {self.projections_file}")
            # Create a dummy template if not exists
            self._create_template()
            
        return pd.read_csv(self.projections_file)
    
    def _create_template(self):
        """Creates a starter template for projections."""
        columns = ['Player', 'Team', 'Pos', 'Salary', 'Projection', 'Sharp_Weight']
        df = pd.DataFrame(columns=columns)
        df.to_csv(self.projections_file, index=False)
        print(f"Created projection template: {self.projections_file}")

if __name__ == "__main__":
    stream = ProjectionStream()
    data = stream.load_projections()
    print(data.head())
