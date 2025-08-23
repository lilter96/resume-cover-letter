"""
Configuration file for HeadHunter Vacancy Parser
"""

# API Configuration
API_CONFIG = {
    'base_url': 'https://api.hh.ru/',
    'rate_limit_delay': 1.5,  # Seconds between requests
    'max_retries': 3,
    'timeout': 30
}

# Search Configuration
SEARCH_CONFIG = {
    'queries': [
        'Data Scientist',
        'Machine Learning Engineer', 
        'ML Engineer',
        'Data Science',
        'Аналитик данных',  # Russian equivalent
        'Машинное обучение'  # Russian equivalent
    ],
    'per_page': 50,
    'max_pages': 3,
    'area': 113,  # Russia (1 - Moscow, 2 - SPb, 113 - Russia)
    'period': 30,  # Days (1, 3, 7, 30)
    'experience': None,  # noExperience, between1And3, between3And6, moreThan6
    'employment': None,  # full, part, project, volunteer, probation
    'schedule': None  # fullDay, shift, flexible, remote, flyInFlyOut
}

# Output Configuration
OUTPUT_CONFIG = {
    'vacancies_file': 'hh_vacancies.csv',
    'frequency_file': 'hh_frequency_stats.csv',
    'log_file': 'hh_parser.log',
    'encoding': 'utf-8'
}

# Technology Detection Lists
TECHNOLOGIES = {
    # Programming Languages
    'python', 'r', 'sql', 'scala', 'java', 'c++', 'julia', 'javascript', 'go', 'rust',
    
    # ML/DL Frameworks
    'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'sklearn', 'xgboost', 'lightgbm', 
    'catboost', 'h2o', 'mlflow', 'kubeflow', 'airflow',
    
    # Data Processing
    'pandas', 'numpy', 'scipy', 'dask', 'polars', 'spark', 'pyspark', 'hadoop',
    
    # Visualization
    'matplotlib', 'seaborn', 'plotly', 'bokeh', 'altair', 'tableau', 'power bi', 
    'qlik', 'looker', 'superset',
    
    # Development Tools
    'jupyter', 'anaconda', 'docker', 'kubernetes', 'git', 'github', 'gitlab',
    
    # Cloud Platforms
    'aws', 'azure', 'gcp', 'google cloud', 'amazon web services', 'yandex cloud',
    
    # Databases
    'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'clickhouse',
    'cassandra', 'neo4j', 'influxdb',
    
    # Web Frameworks
    'fastapi', 'flask', 'django', 'streamlit', 'dash', 'gradio',
    
    # NLP/CV Libraries
    'opencv', 'nltk', 'spacy', 'bert', 'transformers', 'hugging face', 'openai',
    'langchain', 'gensim', 'textblob',
    
    # Big Data
    'kafka', 'rabbitmq', 'celery', 'redis', 'memcached',
    
    # Monitoring & MLOps
    'prometheus', 'grafana', 'wandb', 'tensorboard', 'mlflow', 'dvc'
}

# Keyword Patterns for ML/DS
KEYWORD_PATTERNS = [
    # Core ML/DS Terms
    r'\bmachine learning\b', r'\bml\b', r'\bdeep learning\b', r'\bdl\b',
    r'\bdata science\b', r'\bdata scientist\b', r'\bdata analysis\b',
    r'\bartificial intelligence\b', r'\bai\b', r'\bneural network\b',
    
    # Specialized Areas
    r'\bcomputer vision\b', r'\bcv\b', r'\bnlp\b', r'\bnatural language processing\b',
    r'\brecommendation system\b', r'\btime series\b', r'\bforecasting\b',
    
    # Data Engineering
    r'\bbig data\b', r'\betl\b', r'\bdata mining\b', r'\bdata pipeline\b',
    r'\bdata warehouse\b', r'\bdata lake\b',
    
    # Statistics & Methods
    r'\bstatistics\b', r'\bpredictive modeling\b', r'\bregression\b', 
    r'\bclassification\b', r'\bclustering\b', r'\banomalу detection\b',
    
    # Business & Experimentation
    r'\ba/b testing\b', r'\bexperiment design\b', r'\bbusiness intelligence\b',
    r'\bkpi\b', r'\bmetrics\b',
    
    # Technical Skills
    r'\bfeature engineering\b', r'\bmodel deployment\b', r'\bmlops\b',
    r'\bvisualization\b', r'\bdashboard\b', r'\breporting\b',
    
    # Russian equivalents
    r'\bмашинное обучение\b', r'\bанализ данных\b', r'\bбольшие данные\b',
    r'\bискусственный интеллект\b', r'\bнейронные сети\b'
]

# Logging Configuration
LOGGING_CONFIG = {
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR
    'format': '%(asctime)s - %(levelname)s - %(message)s',
    'file_handler': True,
    'console_handler': True
}

# User Profile Configuration
USER_PROFILE = {
    'name': 'Терентий Гацуков',
    'email': 'lilter96@mail.ru',
    'phone': '+375333854432',
    'experience_years': '1',
    'current_position': 'Intern ML Engineer',
    'key_skills': ['python', 'pandas', 'scikit-learn', 'keras', 'numpy', 'jupyter'],
    'education': 'BSUIR (higher)',
    'achievements': 'Developed predictive models, improved accuracy by 15%',
    'github': 'https://github.com/terentiy',
    'linkedin': 'https://www.linkedin.com/in/terentiy-gatsukov-048694224/',
    'location': 'Minsk, Belarus'
}

# LinkedIn Configuration
LINKEDIN_CONFIG = {
    'enabled': True,
    'parse_on_startup': True,
    'cache_duration_hours': 24,  # Cache parsed data for 24 hours
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}