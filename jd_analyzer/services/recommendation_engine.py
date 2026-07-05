import json
import os
import logging
import copy
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class RecommendationEngine:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.projects_db = self._load_db('project_database.json')
        self.interviews_db = self._load_db('interview_database.json')
        self.roadmaps_db = self._load_db('roadmap_database.json')
        self.experience_db = self._load_db('experience_database.json')

    def _load_db(self, filename: str) -> Dict:
        path = os.path.join(self.base_dir, 'data', filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")
            return {}

    def generate_project_recommendations(self, target_role: str, missing_skills: List[str], required_skills: List[str]) -> List[Dict]:
        projects = []
        seen_titles = set()
        
        # Prioritize missing skills, then required skills
        search_skills = missing_skills + required_skills
        
        for skill in search_skills:
            if not isinstance(skill, str): continue
            skill_lower = skill.strip().lower()
            if skill_lower in self.projects_db:
                for proj in self.projects_db[skill_lower].get('projects', []):
                    if proj['title'] not in seen_titles:
                        projects.append(proj)
                        seen_titles.add(proj['title'])
            if len(projects) >= 3:
                break
                
        # Fallback to default
        if not projects and 'default' in self.projects_db:
            projects.extend(self.projects_db['default'].get('projects', []))
            
        return projects[:3]

    def generate_interview_prep(self, missing_skills: List[str], required_skills: List[str]) -> List[Dict]:
        prep_items = []
        seen_categories = set()
        
        search_skills = missing_skills + required_skills
        
        for skill in search_skills:
            if not isinstance(skill, str): continue
            skill_lower = skill.strip().lower()
            if skill_lower in self.interviews_db:
                item = copy.deepcopy(self.interviews_db[skill_lower])
                if item['category'] not in seen_categories:
                    prep_items.append(item)
                    seen_categories.add(item['category'])
            if len(prep_items) >= 3:
                break
                
        if not prep_items and 'default' in self.interviews_db:
            prep_items.append(self.interviews_db['default'])
            
        return prep_items[:3]

    def generate_experience_improvements(self, target_role: str, missing_skills: List[str]) -> Dict:
        missing_evidence = []
        recommendations = []
        
        for skill in missing_skills:
            if not isinstance(skill, str): continue
            skill_lower = skill.strip().lower()
            if skill_lower in self.experience_db:
                missing_evidence.extend(self.experience_db[skill_lower].get('missing_evidence', []))
                recommendations.extend(self.experience_db[skill_lower].get('recommendations', []))
            else:
                default = self.experience_db.get('default', {})
                missing_evidence.extend([m.replace("{skill}", skill) for m in default.get('missing_evidence', [])])
                recommendations.extend([r.replace("{skill}", skill) for r in default.get('recommendations', [])])
                
        # Deduplicate
        missing_evidence = list(dict.fromkeys(missing_evidence))
        recommendations = list(dict.fromkeys(recommendations))
        
        if not missing_evidence:
            missing_evidence = ["Targeted industry experience"]
            recommendations = ["Your experience perfectly matches the requirements. Focus on interview prep."]
            
        return {
            "missing_evidence": missing_evidence[:5],
            "recommendations": recommendations[:5]
        }

    def generate_roadmap_phases(self, target_role: str, target_company: str, missing_skills: List[str], required_skills: List[str]) -> List[Dict]:
        phases = []
        
        # Check role-based templates first
        roles_db = self.roadmaps_db.get('roles', {})
        role_matched = False
        
        # Substring match for roles (e.g., "Teaching Ninja" in "Kalvium Teaching Ninjas (DSA + Tech Skilling)")
        for role_key, role_phases in roles_db.items():
            if role_key.lower() in target_role.lower():
                phases.extend(role_phases)
                role_matched = True
                break
                
        if role_matched:
            return phases
            
        # Fallback to skill-based generation
        skills_db = self.roadmaps_db.get('skills', {})
        search_skills = missing_skills if missing_skills else required_skills
        
        for idx, skill in enumerate(search_skills[:4], start=1):
            if not isinstance(skill, str): continue
            skill_lower = skill.strip().lower()
            if skill_lower in skills_db:
                phase_data = copy.deepcopy(skills_db[skill_lower])
                phase_data['phase'] = phase_data['phase'].replace("{skill}", skill)
                phases.append(phase_data)
            else:
                phase_data = copy.deepcopy(skills_db.get('default', {}))
                if 'phase' in phase_data:
                    phase_data['phase'] = phase_data['phase'].replace("{skill}", skill.strip())
                for i in range(len(phase_data.get('objectives', []))):
                    phase_data['objectives'][i] = phase_data['objectives'][i].replace("{skill}", skill.strip())
                for i in range(len(phase_data.get('activities', []))):
                    phase_data['activities'][i] = phase_data['activities'][i].replace("{skill}", skill.strip())
                phases.append(phase_data)
                
        if not phases:
            phases.append({
                "phase": "General Interview Preparation",
                "duration": "2 Weeks",
                "objectives": ["Solidify existing knowledge"],
                "activities": ["Review industry trends", "Practice behavioral questions"],
                "deliverables": ["Mock interview completion"],
                "success_criteria": "Interview Readiness"
            })
            
        return phases
