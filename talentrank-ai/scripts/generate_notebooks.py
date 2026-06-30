"""
Script to generate the EDA notebooks for TalentRank AI.
Uses nbformat to construct well-formed Jupyter notebooks.
"""

import sys
from pathlib import Path

# Try to import nbformat; if missing, we'll install it later,
# but we can write the script now.
try:
    import nbformat
    from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell
except ImportError:
    pass

PROJECT_ROOT = Path(r"c:\Users\ssake\Downloads\TalentRank AI\talentrank-ai")
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
NOTEBOOKS_DIR.mkdir(exist_ok=True)


def create_notebook_01():
    nb = new_notebook()
    nb.cells.extend([
        new_markdown_cell("# TalentRank AI: Dataset Overview\n\nThis notebook provides a high-level overview of the candidate dataset (100k records). We will analyze the missingness, schema compliance, and basic distributions of the core fields."),
        new_code_cell("import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport json\nfrom pathlib import Path\n\nimport sys\nsys.path.insert(0, '../')\nfrom src.config.settings import get_settings\nfrom src.utils.io import load_jsonl\n\nsettings = get_settings()\nsns.set_theme(style='whitegrid')"),
        new_markdown_cell("## 1. Load Data Sample\nWe load a sample of the data to avoid memory issues during initial exploration."),
        new_code_cell("candidates = list(load_jsonl(settings.paths.candidates_jsonl, max_records=10000))\nprint(f'Loaded {len(candidates)} candidates.')"),
        new_markdown_cell("## 2. Basic Profile Distributions"),
        new_code_cell("# Experience Distribution\nexperience = [c['profile'].get('years_of_experience', 0) for c in candidates]\nplt.figure(figsize=(10, 6))\nsns.histplot(experience, bins=30, kde=True)\nplt.title('Distribution of Years of Experience')\nplt.xlabel('Years')\nplt.ylabel('Count')\nplt.show()"),
        new_code_cell("# Current Industry Distribution\nindustries = [c['profile'].get('current_industry', 'Unknown') for c in candidates]\nind_series = pd.Series(industries).value_counts().head(10)\nplt.figure(figsize=(10, 6))\nsns.barplot(y=ind_series.index, x=ind_series.values)\nplt.title('Top 10 Current Industries')\nplt.show()"),
    ])
    nbformat.write(nb, str(NOTEBOOKS_DIR / "01_dataset_overview.ipynb"))
    print("Created 01_dataset_overview.ipynb")


def create_notebook_02():
    nb = new_notebook()
    nb.cells.extend([
        new_markdown_cell("# TalentRank AI: Behavioral Signal Analysis\n\nAnalyzing the `redrob_signals` object. These signals are critical for determining if a candidate is hirable (active, responsive, open to work)."),
        new_code_cell("import pandas as pd\nimport numpy as np\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport sys\n\nsys.path.insert(0, '../')\nfrom src.config.settings import get_settings\nfrom src.utils.io import load_jsonl\n\nsettings = get_settings()\nsns.set_theme(style='whitegrid')"),
        new_code_cell("candidates = list(load_jsonl(settings.paths.candidates_jsonl, max_records=10000))\nsignals = [c.get('redrob_signals', {}) for c in candidates]\ndf = pd.DataFrame(signals)\ndf.head()"),
        new_markdown_cell("## Response Rates & Activity"),
        new_code_cell("plt.figure(figsize=(10, 6))\nsns.histplot(df['recruiter_response_rate'].dropna(), bins=20)\nplt.title('Recruiter Response Rate Distribution')\nplt.xlabel('Response Rate (0-1)')\nplt.show()"),
        new_code_cell("plt.figure(figsize=(10, 6))\nsns.histplot(df['profile_completeness_score'].dropna(), bins=20)\nplt.title('Profile Completeness Score')\nplt.show()"),
        new_markdown_cell("## Salary Expectations"),
        new_code_cell("salaries = [s.get('expected_salary_range_inr_lpa', {}) for s in signals]\nsal_df = pd.DataFrame(salaries)\n\nplt.figure(figsize=(10, 6))\nsns.scatterplot(data=sal_df, x='min', y='max', alpha=0.5)\nplt.title('Salary Expectations (Min vs Max LPA)')\nplt.plot([0, 80], [0, 80], 'r--', label='Min=Max')\nplt.legend()\nplt.show()"),
    ])
    nbformat.write(nb, str(NOTEBOOKS_DIR / "02_behavioral_analysis.ipynb"))
    print("Created 02_behavioral_analysis.ipynb")


def create_notebook_03():
    nb = new_notebook()
    nb.cells.extend([
        new_markdown_cell("# TalentRank AI: Skill & Experience Analysis\n\nAnalyzing the skills array and its relation to career history."),
        new_code_cell("import pandas as pd\nimport matplotlib.pyplot as plt\nimport seaborn as sns\nimport sys\nsys.path.insert(0, '../')\nfrom src.utils.io import load_jsonl\nfrom src.config.settings import get_settings\n\ncandidates = list(load_jsonl(get_settings().paths.candidates_jsonl, max_records=10000))"),
        new_code_cell("all_skills = []\nfor c in candidates:\n    all_skills.extend([s.get('name', '').lower() for s in c.get('skills', [])])\n\nskill_counts = pd.Series(all_skills).value_counts().head(20)\nplt.figure(figsize=(12, 8))\nsns.barplot(y=skill_counts.index, x=skill_counts.values)\nplt.title('Top 20 Skills Overall')\nplt.show()"),
    ])
    nbformat.write(nb, str(NOTEBOOKS_DIR / "03_skill_and_experience_analysis.ipynb"))
    print("Created 03_skill_and_experience_analysis.ipynb")


def create_notebook_04():
    nb = new_notebook()
    nb.cells.extend([
        new_markdown_cell("# TalentRank AI: Company and Title Analysis"),
        new_code_cell("import pandas as pd\nimport sys\nsys.path.insert(0, '../')\nfrom src.utils.io import load_jsonl\nfrom src.config.settings import get_settings\n\ncandidates = list(load_jsonl(get_settings().paths.candidates_jsonl, max_records=10000))")
    ])
    nbformat.write(nb, str(NOTEBOOKS_DIR / "04_company_and_title_analysis.ipynb"))
    print("Created 04_company_and_title_analysis.ipynb")


def create_notebook_05():
    nb = new_notebook()
    nb.cells.extend([
        new_markdown_cell("# TalentRank AI: Honeypot Detection\n\nThe dataset contains ~80 honeypots (keyword stuffers, impossible profiles). We will visualize the rules that detect them."),
        new_code_cell("import pandas as pd\nimport sys\nsys.path.insert(0, '../')\nfrom src.utils.io import load_jsonl\nfrom src.config.settings import get_settings\n\ncandidates = list(load_jsonl(get_settings().paths.candidates_jsonl, max_records=10000))")
    ])
    nbformat.write(nb, str(NOTEBOOKS_DIR / "05_honeypot_detection.ipynb"))
    print("Created 05_honeypot_detection.ipynb")


def create_notebook_06():
    nb = new_notebook()
    nb.cells.extend([
        new_markdown_cell("# TalentRank AI: Feature Engineering Analysis\n\nAnalyzing the final extracted features."),
        new_code_cell("import pandas as pd\nimport sys\nsys.path.insert(0, '../')\nfrom src.features.store import FeatureStore\nfrom src.config.settings import get_settings\n\n# We will load the feature store once it is generated.")
    ])
    nbformat.write(nb, str(NOTEBOOKS_DIR / "06_feature_engineering_analysis.ipynb"))
    print("Created 06_feature_engineering_analysis.ipynb")


if __name__ == '__main__':
    create_notebook_01()
    create_notebook_02()
    create_notebook_03()
    create_notebook_04()
    create_notebook_05()
    create_notebook_06()
