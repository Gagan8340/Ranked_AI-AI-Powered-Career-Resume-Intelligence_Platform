import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

print("--- INITIALIZING JD ANALYZER PIPELINE ---")
try:
    from jd_analyzer.services.jd_analyzer import JDAnalyzerService
    analyzer = JDAnalyzerService()
    
    print("\n--- RUNNING ANALYSIS ---")
    jd_text = "We are looking for a Senior Software Engineer with strong Python, AWS, and Docker skills. 5+ years experience required."
    resume_text = "I am a software engineer with 5 years of experience in Python and Kubernetes."
    
    res = analyzer.analyze(jd_text, resume_text)
    print("\n--- SUCCESS ---")
    print("JD Analyzer operates with the full NLP/ML pipeline!")
except Exception as e:
    print(f"Error: {e}")
