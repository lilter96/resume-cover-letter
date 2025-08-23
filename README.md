# HeadHunter Vacancy Parser

A Python script to parse HeadHunter (hh.ru) vacancies for Data Science and Machine Learning positions, extract keywords and technologies using AI/LLM, and export the data to CSV format.

## Features

- **API Integration**: Uses HeadHunter's official API with proper rate limiting (1-2 requests per second)
- **🤖 LLM-Powered Extraction**: Intelligent keyword and technology extraction using OpenRouter LLMs (Claude, GPT-4, etc.)
- **Smart Fallback**: Automatic fallback to regex-based extraction if LLM is unavailable
- **Enhanced Analysis**: Extracts keywords, technologies, skills, experience levels, and domain focus
- **Frequency Analysis**: Identifies most common patterns across all parsed vacancies
- **Structured CSV Export**: Exports comprehensive data with enhanced fields
- **Error Handling**: Comprehensive logging and error handling for robust operation

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r scripts/requirements.txt
```

3. (Optional) Set up OpenRouter API for LLM-powered extraction:
```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

## Usage

### Basic Usage (Regex-based extraction)
```bash
python scripts/hh.py
```

### LLM-Enhanced Usage
1. Get an API key from [OpenRouter](https://openrouter.ai/)
2. Set up your environment:
```bash
export OPENROUTER_API_KEY="your_api_key_here"
# Or edit .env file
```
3. Run the script:
```bash
python scripts/hh.py
```

The script will:
1. Search for vacancies using predefined queries: "Data Scientist", "Machine Learning Engineer", "ML Engineer", "Data Science"
2. Extract detailed information for each vacancy
3. Use LLM to intelligently analyze job descriptions (or fallback to regex)
4. Export enhanced results to CSV files

## Output Files

- `hh_vacancies.csv` - Main results with vacancy details
- `hh_frequency_stats.csv` - Frequency analysis of keywords and technologies
- `hh_parser.log` - Detailed execution log

## CSV Structure

### hh_vacancies.csv
| Column | Description |
|--------|-------------|
| vacancy_title | Job title |
| company | Company name |
| keywords | Comma-separated ML/DS keywords found |
| technologies | Comma-separated technologies/tools found |
| skills | Comma-separated soft skills and domain expertise |
| experience_level | Required experience level (Junior/Middle/Senior/Lead/Principal) |
| domain | Primary industry/domain focus |
| salary | Salary information (if available) |
| url | Direct link to vacancy |

### hh_frequency_stats.csv
Contains comprehensive frequency analysis:
- **Top Keywords**: Most frequent ML/DS keywords with counts
- **Top Technologies**: Most frequent technologies/tools with counts
- **Top Skills**: Most frequent soft skills and expertise areas
- **Experience Levels**: Distribution of experience requirements
- **Domains**: Most common industry/domain focuses

## LLM-Powered Extraction

When OpenRouter API is configured, the script uses advanced LLM analysis to extract:

### 🎯 Intelligent Recognition
- **Context-Aware**: Understands job descriptions contextually, not just keyword matching
- **Semantic Analysis**: Recognizes synonyms, abbreviations, and industry terminology
- **Structured Output**: Consistent, well-formatted extraction results

### 📊 Enhanced Categories
- **Keywords**: ML/DS concepts (machine learning, deep learning, NLP, computer vision, etc.)
- **Technologies**: Programming languages, frameworks, tools, platforms
- **Skills**: Soft skills, domain expertise, methodological knowledge
- **Experience Level**: Automatically determined seniority requirements
- **Domain Focus**: Industry/business domain identification

### 🔄 Fallback System
- **Regex Backup**: Automatic fallback to pattern-based extraction if LLM fails
- **Robust Operation**: Continues processing even with API issues
- **Cost Optimization**: Efficient prompt design to minimize API costs

## Traditional Technology Detection (Fallback)

When LLM is unavailable, regex-based detection includes:
- **Languages**: Python, R, SQL, Scala, Java, C++, Julia
- **ML Frameworks**: TensorFlow, PyTorch, Keras, Scikit-learn
- **Data Tools**: Pandas, NumPy, SciPy, Matplotlib, Seaborn, Plotly
- **Platforms**: Jupyter, Anaconda, Docker, Kubernetes
- **Cloud Services**: AWS, Azure, GCP
- **Databases**: PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch

## Configuration

You can modify the script to:
- Change search queries in the `main()` function
- Adjust rate limiting in `HeadHunterAPI.__init__()`
- Add new technologies in `VacancyProcessor.TECHNOLOGIES`
- Add new keyword patterns in `VacancyProcessor.KEYWORDS_PATTERNS`
- Modify search parameters (area, pages, etc.)

## Rate Limiting

The script respects HeadHunter's API limits with:
- 1.5-second delay between requests (configurable)
- Proper error handling for rate limit responses
- Exponential backoff for failed requests

## Logging

Comprehensive logging includes:
- API request details
- Processing progress
- Error messages with details
- Summary statistics

## Legal Notice

This script is for educational and research purposes. Please ensure compliance with HeadHunter's Terms of Service and API usage policies when using this tool.

## Troubleshooting

### Common Issues

1. **400 Bad Request**: Usually caused by invalid User-Agent header (fixed in current version)
2. **Rate Limiting**: Script automatically handles rate limits with delays
3. **No Results**: Check if search queries are appropriate for the target market

### Debug Mode

To enable debug logging, modify the logging level in the script:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Example Output

```
=== SUMMARY ===
Total vacancies processed: 150
Results exported to: hh_vacancies.csv
Frequency stats exported to: hh_frequency_stats.csv

Top 10 Technologies:
  python: 89
  sql: 67
  pandas: 45
  scikit-learn: 34
  tensorflow: 28
  ...

Top 10 Keywords:
  machine learning: 78
  data analysis: 56
  deep learning: 34
  data science: 89
  ...