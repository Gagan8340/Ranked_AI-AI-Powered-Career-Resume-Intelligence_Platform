import sys
sys.path.append(r'd:\smartcampus\smartcampus-ai')
from jd_analyzer.services.jd_validator import JDValidatorService

jds = [
    {
        'name': 'Real JD',
        'text': '''
        Data Scientist
        Location: Remote
        Full Time
        
        Responsibilities:
        - Analyze data using Python
        - Build models
        - Deploy models
        
        Requirements:
        - 3+ years experience
        - Python, SQL
        This is extra text to ensure the length is more than 100 characters so that it passes the minimum content length check accurately. It requires at least 20 words as well.
        '''
    },
    {
        'name': 'Partial JD',
        'text': '''
        We are looking for a developer. Must know python and sql. Work remote. We really need someone who can work on this as soon as possible because we are very behind on this project. Need experience.
        '''
    },
    {
        'name': 'Random Text',
        'text': '''
        Hello there, this is just a quick note about nothing in particular.
        I hope you are doing well. Please find the attached document.
        Let me know what you think. Thanks! We need this for the next quarter. I will talk to you soon. This has a lot of words so it passes the length check.
        '''
    },
    {
        'name': 'Gibberish',
        'text': '''
        asdffghjklkjhg zxcvbnm qwerttyyuiiopp
        fbfbfbfbfb hello xyz xcvb qwert
        fdfdfdfd asdfasdf
        Some extra text here so that it passes the length test.
        Wait I need to make it longer so the 100 char limit doesn't just block it for length instead of gibberish.
        '''
    }
]

validator = JDValidatorService()
for jd in jds:
    print('--- ' + jd['name'] + ' ---')
    res = validator.validate(jd['text'])
    print(f"Valid: {res['valid_jd']}, Confidence: {res['confidence']}, Message: {res['message']}")
