# Tension Board ML Generator

A machine learning model to generate climbing problems for the Tension Board.

## Setup

1. Clone the repository

```bash
git clone [your-repo-url]
cd tension-board-ml
```

2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your credentials
```

## Usage

1. Prepare data:

```bash
python src/data_prep.py
```

2. Train model:

```bash
python src/train.py
```

3. Generate problems:

```bash
python src/generate.py
```

## Project Structure

```
tension-board-ml/
├── data/
│   ├── raw/         # Raw climbing data
│   └── processed/   # Processed data for training
├── src/
│   ├── train.py     # Training script
│   ├── data_prep.py # Data preparation
│   └── generate.py  # Problem generation
├── models/          # Saved models
├── tests/           # Test files
├── requirements.txt # Project dependencies
└── README.md       # Project documentation
```

## Environment Variables

Create a `.env` file with:

```
HUGGINGFACE_TOKEN=your_token_here
HUGGINGFACE_USERNAME=your_username
```
