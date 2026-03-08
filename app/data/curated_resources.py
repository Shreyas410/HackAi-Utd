"""
Curated YouTube video recommendations.

This is a SMALL, maintainable database of actual YouTube video URLs.
Each entry contains a DIRECT link to a real video, not a search URL.

Platform: YouTube only
"""

from typing import Dict, List, Any, Optional


# Curated YouTube video resources for common skills
CURATED_RESOURCES: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    
    # ==================== NODE.JS ====================
    "nodejs": {
        "beginner": [
            {
                "title": "Node.js Tutorial for Beginners: Learn Node in 1 Hour",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=TlB_eWDSMt4",
                "resource_type": "video",
                "description": "Fast-paced intro to Node.js fundamentals by Programming with Mosh",
                "reason": "Excellent starting point - covers core concepts in 1 hour",
                "is_free": True,
                "duration_hours": 1
            },
            {
                "title": "Node.js Full Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=f2EqECiTBL8",
                "resource_type": "video",
                "description": "Complete 7-hour Node.js tutorial by Dave Gray",
                "reason": "Comprehensive beginner course with hands-on projects",
                "is_free": True,
                "duration_hours": 7
            }
        ],
        "intermediate": [
            {
                "title": "Node.js and Express.js - Full Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=Oe421EPjeBE",
                "resource_type": "video",
                "description": "8-hour freeCodeCamp course on Node and Express",
                "reason": "Deep dive into Express framework and REST APIs",
                "is_free": True,
                "duration_hours": 8
            }
        ],
        "advanced": [
            {
                "title": "Node.js Design Patterns",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=tv-_1er1mWI",
                "resource_type": "video",
                "description": "Advanced Node.js patterns and architecture",
                "reason": "Master production-grade Node.js patterns",
                "is_free": True,
                "duration_hours": 2
            }
        ]
    },
    
    # ==================== EXPRESS.JS ====================
    "expressjs": {
        "beginner": [
            {
                "title": "Express JS Crash Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=L72fhGm1tfE",
                "resource_type": "video",
                "description": "Traversy Media Express.js crash course",
                "reason": "Quick introduction to Express fundamentals",
                "is_free": True,
                "duration_hours": 1.5
            }
        ],
        "intermediate": [
            {
                "title": "Node.js and Express.js - Full Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=Oe421EPjeBE",
                "resource_type": "video",
                "description": "Complete Express.js with Node.js by freeCodeCamp",
                "reason": "Build complete REST APIs with Express",
                "is_free": True,
                "duration_hours": 8
            }
        ],
        "advanced": [
            {
                "title": "Express.js Production Best Practices",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=CTnzgzRPBwA",
                "resource_type": "video",
                "description": "Production-grade Express.js patterns",
                "reason": "Learn deployment and scaling strategies",
                "is_free": True,
                "duration_hours": 1
            }
        ]
    },
    
    # ==================== MONGODB ====================
    "mongodb": {
        "beginner": [
            {
                "title": "MongoDB Crash Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=-56x56UppqQ",
                "resource_type": "video",
                "description": "Traversy Media MongoDB crash course",
                "reason": "Quick intro to MongoDB basics and CRUD operations",
                "is_free": True,
                "duration_hours": 1.5
            }
        ],
        "intermediate": [
            {
                "title": "MongoDB Complete Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=c2M-rlkkT5o",
                "resource_type": "video",
                "description": "Complete MongoDB tutorial with Node.js",
                "reason": "Full MongoDB with practical examples",
                "is_free": True,
                "duration_hours": 4
            }
        ],
        "advanced": [
            {
                "title": "MongoDB Performance Tuning",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=mzHQwMtAOdo",
                "resource_type": "video",
                "description": "Advanced MongoDB optimization techniques",
                "reason": "Learn indexing and query optimization",
                "is_free": True,
                "duration_hours": 1
            }
        ]
    },
    
    # ==================== REACT ====================
    "react": {
        "beginner": [
            {
                "title": "React Course - Beginner's Tutorial for React JavaScript Library",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=bMknfKXIFA8",
                "resource_type": "video",
                "description": "12-hour freeCodeCamp React tutorial",
                "reason": "Comprehensive beginner course with modern React",
                "is_free": True,
                "duration_hours": 12
            }
        ],
        "intermediate": [
            {
                "title": "Full React Course 2020 - Learn Fundamentals, Hooks, Context API",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=4UZrsTqkcW4",
                "resource_type": "video",
                "description": "freeCodeCamp React with Hooks and Context",
                "reason": "Master modern React patterns",
                "is_free": True,
                "duration_hours": 10
            },
            {
                "title": "React Testing Library Tutorial",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=7dTTFW7yACQ",
                "resource_type": "video",
                "description": "Complete React testing guide",
                "reason": "Learn to test React applications",
                "is_free": True,
                "duration_hours": 2
            }
        ],
        "advanced": [
            {
                "title": "React Performance Optimization",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=5fLW5Q5ODiE",
                "resource_type": "video",
                "description": "Advanced React optimization techniques",
                "reason": "Master React performance tuning",
                "is_free": True,
                "duration_hours": 1
            }
        ]
    },
    
    # ==================== JAVASCRIPT ====================
    "javascript": {
        "beginner": [
            {
                "title": "JavaScript Tutorial Full Course - Beginner to Pro",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=SBmSRK3feww",
                "resource_type": "video",
                "description": "SuperSimpleDev 8-hour JavaScript course",
                "reason": "Modern JavaScript from scratch",
                "is_free": True,
                "duration_hours": 8
            },
            {
                "title": "Learn JavaScript - Full Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=PkZNo7MFNFg",
                "resource_type": "video",
                "description": "freeCodeCamp JavaScript fundamentals",
                "reason": "Comprehensive JS basics",
                "is_free": True,
                "duration_hours": 3.5
            }
        ],
        "intermediate": [
            {
                "title": "JavaScript Algorithms and Data Structures",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=t2CEgPsws3U",
                "resource_type": "video",
                "description": "JS algorithms and data structures",
                "reason": "Master DSA with JavaScript",
                "is_free": True,
                "duration_hours": 8
            },
            {
                "title": "Asynchronous JavaScript Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=ZYb_ZU8LNxs",
                "resource_type": "video",
                "description": "Async JS - Callbacks, Promises, Async/Await",
                "reason": "Deep dive into async JavaScript",
                "is_free": True,
                "duration_hours": 1.5
            }
        ],
        "advanced": [
            {
                "title": "JavaScript Design Patterns",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=kuirGzhGhyw",
                "resource_type": "video",
                "description": "Deep dive into JS design patterns",
                "reason": "Understand advanced JS patterns",
                "is_free": True,
                "duration_hours": 2
            }
        ]
    },
    
    # ==================== PYTHON ====================
    "python": {
        "beginner": [
            {
                "title": "Python Tutorial - Python Full Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc",
                "resource_type": "video",
                "description": "Programming with Mosh 6-hour Python course",
                "reason": "Best-rated Python beginner tutorial",
                "is_free": True,
                "duration_hours": 6
            },
            {
                "title": "Learn Python - Full Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=rfscVS0vtbw",
                "resource_type": "video",
                "description": "freeCodeCamp Python tutorial",
                "reason": "Comprehensive Python fundamentals",
                "is_free": True,
                "duration_hours": 4.5
            }
        ],
        "intermediate": [
            {
                "title": "Intermediate Python Programming Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=HGOBQPFzWKo",
                "resource_type": "video",
                "description": "freeCodeCamp intermediate Python",
                "reason": "OOP, decorators, and advanced concepts",
                "is_free": True,
                "duration_hours": 6
            },
            {
                "title": "Python OOP - Object Oriented Programming for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=Ej_02ICOIgs",
                "resource_type": "video",
                "description": "Complete Python OOP tutorial",
                "reason": "Master object-oriented Python",
                "is_free": True,
                "duration_hours": 2
            }
        ],
        "advanced": [
            {
                "title": "Advanced Python - Complete Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=QLTdOEn79Rc",
                "resource_type": "video",
                "description": "NeuralNine advanced Python concepts",
                "reason": "Decorators, generators, metaclasses",
                "is_free": True,
                "duration_hours": 3
            }
        ]
    },
    
    # ==================== SQL ====================
    "sql": {
        "beginner": [
            {
                "title": "SQL Tutorial - Full Database Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=HXV3zeQKqGY",
                "resource_type": "video",
                "description": "freeCodeCamp 4-hour SQL course",
                "reason": "Complete SQL fundamentals",
                "is_free": True,
                "duration_hours": 4
            },
            {
                "title": "MySQL Tutorial for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=7S_tz1z_5bA",
                "resource_type": "video",
                "description": "Programming with Mosh MySQL course",
                "reason": "Practical MySQL skills",
                "is_free": True,
                "duration_hours": 3
            }
        ],
        "intermediate": [
            {
                "title": "Advanced SQL Tutorial",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=M-55BmjOuXY",
                "resource_type": "video",
                "description": "Advanced SQL queries and optimization",
                "reason": "Window functions, CTEs, subqueries",
                "is_free": True,
                "duration_hours": 3
            }
        ],
        "advanced": [
            {
                "title": "SQL Performance Explained",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=BHwzDmr6d7s",
                "resource_type": "video",
                "description": "SQL indexing and optimization",
                "reason": "Master query performance tuning",
                "is_free": True,
                "duration_hours": 1
            }
        ]
    },
    
    # ==================== DATA STRUCTURES ====================
    "data structures": {
        "beginner": [
            {
                "title": "Data Structures Easy to Advanced Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=RBSGKlAvoiM",
                "resource_type": "video",
                "description": "freeCodeCamp 8-hour DSA course",
                "reason": "Comprehensive data structures tutorial",
                "is_free": True,
                "duration_hours": 8
            }
        ],
        "intermediate": [
            {
                "title": "Graph Algorithms for Technical Interviews",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=tWVWeAqZ0WU",
                "resource_type": "video",
                "description": "freeCodeCamp graph algorithms",
                "reason": "Master graph traversal and problems",
                "is_free": True,
                "duration_hours": 2
            }
        ],
        "advanced": [
            {
                "title": "Advanced Data Structures",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=0JUN9aDxVmI",
                "resource_type": "video",
                "description": "MIT OpenCourseWare advanced DSA",
                "reason": "Academic deep dive into advanced structures",
                "is_free": True,
                "duration_hours": 1.5
            }
        ]
    },
    
    # ==================== ALGORITHMS ====================
    "algorithms": {
        "beginner": [
            {
                "title": "Algorithms and Data Structures Tutorial - Full Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=8hly31xKli0",
                "resource_type": "video",
                "description": "freeCodeCamp algorithms course",
                "reason": "Comprehensive algorithms introduction",
                "is_free": True,
                "duration_hours": 5
            }
        ],
        "intermediate": [
            {
                "title": "Dynamic Programming - Learn to Solve Algorithmic Problems",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=oBt53YbR9Kk",
                "resource_type": "video",
                "description": "freeCodeCamp dynamic programming",
                "reason": "Master DP problem-solving patterns",
                "is_free": True,
                "duration_hours": 5
            }
        ],
        "advanced": [
            {
                "title": "MIT 6.006 Introduction to Algorithms",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=HtSuA80QTyo",
                "resource_type": "video",
                "description": "MIT algorithms lecture series",
                "reason": "Academic-level algorithm analysis",
                "is_free": True,
                "duration_hours": 20
            }
        ]
    },
    
    # ==================== DYNAMIC PROGRAMMING ====================
    "dynamic programming": {
        "beginner": [
            {
                "title": "Dynamic Programming - Learn to Solve Algorithmic Problems",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=oBt53YbR9Kk",
                "resource_type": "video",
                "description": "freeCodeCamp 5-hour DP course",
                "reason": "Best DP tutorial for beginners",
                "is_free": True,
                "duration_hours": 5
            }
        ],
        "intermediate": [
            {
                "title": "Mastering Dynamic Programming - Top Interview Questions",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=Hdr64lKQ3e4",
                "resource_type": "video",
                "description": "DP interview preparation",
                "reason": "Practice common DP patterns",
                "is_free": True,
                "duration_hours": 5
            }
        ],
        "advanced": [
            {
                "title": "Advanced Dynamic Programming Techniques",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=FAQxdm0bTaw",
                "resource_type": "video",
                "description": "Bitmask DP and optimization",
                "reason": "Advanced DP optimization techniques",
                "is_free": True,
                "duration_hours": 2
            }
        ]
    },
    
    # ==================== MACHINE LEARNING ====================
    "machine learning": {
        "beginner": [
            {
                "title": "Machine Learning Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=NWONeJKn6kc",
                "resource_type": "video",
                "description": "freeCodeCamp ML fundamentals",
                "reason": "Comprehensive ML introduction",
                "is_free": True,
                "duration_hours": 10
            }
        ],
        "intermediate": [
            {
                "title": "Machine Learning with Python and Scikit-Learn",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=pqNCD_5r0IU",
                "resource_type": "video",
                "description": "Practical ML with scikit-learn",
                "reason": "Build real ML models",
                "is_free": True,
                "duration_hours": 18
            }
        ],
        "advanced": [
            {
                "title": "Deep Learning Full Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=VyWAvY2CF9c",
                "resource_type": "video",
                "description": "Complete deep learning tutorial",
                "reason": "Neural networks and deep learning",
                "is_free": True,
                "duration_hours": 6
            }
        ]
    },
    
    # ==================== FASTAPI ====================
    "fastapi": {
        "beginner": [
            {
                "title": "FastAPI Course for Beginners",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=tLKKmouUams",
                "resource_type": "video",
                "description": "freeCodeCamp FastAPI tutorial",
                "reason": "Complete FastAPI introduction",
                "is_free": True,
                "duration_hours": 6
            }
        ],
        "intermediate": [
            {
                "title": "FastAPI Full Stack Application",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=0sOvCWFmrtA",
                "resource_type": "video",
                "description": "Build full-stack apps with FastAPI",
                "reason": "Real-world FastAPI projects",
                "is_free": True,
                "duration_hours": 4
            }
        ],
        "advanced": [
            {
                "title": "FastAPI Beyond CRUD",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=TO4aQ3ghFOc",
                "resource_type": "video",
                "description": "Advanced FastAPI patterns",
                "reason": "Production FastAPI architecture",
                "is_free": True,
                "duration_hours": 8
            }
        ]
    },
    
    # ==================== SYSTEM DESIGN ====================
    "system design": {
        "beginner": [
            {
                "title": "System Design for Beginners Course",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=MbjObHmDbZo",
                "resource_type": "video",
                "description": "ByteByteGo system design basics",
                "reason": "Introduction to system design concepts",
                "is_free": True,
                "duration_hours": 1
            }
        ],
        "intermediate": [
            {
                "title": "System Design Interview - An insider's guide",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=bUHFg8CZFws",
                "resource_type": "video",
                "description": "System design interview preparation",
                "reason": "Prepare for system design interviews",
                "is_free": True,
                "duration_hours": 2
            }
        ],
        "advanced": [
            {
                "title": "System Design Interview - Step By Step Guide",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=i7twT3x5yv8",
                "resource_type": "video",
                "description": "Advanced system design walkthrough",
                "reason": "Design complex distributed systems",
                "is_free": True,
                "duration_hours": 2
            }
        ]
    },
    
    # ==================== AWS ====================
    "aws": {
        "beginner": [
            {
                "title": "AWS Certified Cloud Practitioner Training",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=SOTamWNgDKc",
                "resource_type": "video",
                "description": "freeCodeCamp AWS Cloud Practitioner course",
                "reason": "Complete AWS fundamentals for certification",
                "is_free": True,
                "duration_hours": 14
            }
        ],
        "intermediate": [
            {
                "title": "AWS Solutions Architect Associate",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=Ia-UEYYR44s",
                "resource_type": "video",
                "description": "AWS Solutions Architect training",
                "reason": "Design scalable AWS architectures",
                "is_free": True,
                "duration_hours": 10
            }
        ],
        "advanced": [
            {
                "title": "AWS Advanced Networking",
                "platform": "youtube",
                "url": "https://www.youtube.com/watch?v=hiKPPy584Mg",
                "resource_type": "video",
                "description": "Advanced AWS networking concepts",
                "reason": "Master AWS networking and security",
                "is_free": True,
                "duration_hours": 3
            }
        ]
    }
}

# Skill name aliases for matching
SKILL_ALIASES: Dict[str, str] = {
    "node": "nodejs",
    "node.js": "nodejs",
    "express": "expressjs",
    "express.js": "expressjs",
    "mongo": "mongodb",
    "reactjs": "react",
    "react.js": "react",
    "js": "javascript",
    "py": "python",
    "dsa": "data structures",
    "ds": "data structures",
    "algo": "algorithms",
    "dp": "dynamic programming",
    "ml": "machine learning",
    "fast api": "fastapi",
    "sysdes": "system design",
    "amazon web services": "aws"
}

# Generic YouTube fallbacks for unknown skills by level
GENERIC_DIRECT_RESOURCES: Dict[str, List[Dict[str, Any]]] = {
    "beginner": [
        {
            "title": "CS50: Introduction to Computer Science",
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=8mAITcNt710",
            "resource_type": "video",
            "description": "Harvard's CS50 - best intro to programming",
            "reason": "World-class introduction to computer science",
            "is_free": True,
            "duration_hours": 25
        },
        {
            "title": "Programming Fundamentals",
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=zOjov-2OZ0E",
            "resource_type": "video",
            "description": "Introduction to programming concepts",
            "reason": "Solid programming fundamentals",
            "is_free": True,
            "duration_hours": 4
        }
    ],
    "intermediate": [
        {
            "title": "Software Engineering Full Course",
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=uJGO4HQLLRU",
            "resource_type": "video",
            "description": "Complete software engineering concepts",
            "reason": "Learn professional software development",
            "is_free": True,
            "duration_hours": 8
        }
    ],
    "advanced": [
        {
            "title": "MIT 6.824: Distributed Systems",
            "platform": "youtube",
            "url": "https://www.youtube.com/watch?v=cQP8WApzIQQ",
            "resource_type": "video",
            "description": "MIT's distributed systems course",
            "reason": "World-class distributed systems education",
            "is_free": True,
            "duration_hours": 20
        }
    ]
}

# Level-specific query modifiers (for YouTube search fallback)
LEVEL_MODIFIERS = {
    "beginner": ["beginner", "fundamentals", "introduction", "basics", "crash course"],
    "intermediate": ["intermediate", "hands-on", "practical", "projects", "in-depth"],
    "advanced": ["advanced", "deep dive", "mastery", "expert", "architecture"]
}


def normalize_skill_name(skill: str) -> str:
    """Normalize skill name to match curated keys."""
    skill_lower = skill.lower().strip()
    return SKILL_ALIASES.get(skill_lower, skill_lower)


def get_curated_resources(skill: str, level: str) -> List[Dict[str, Any]]:
    """
    Get curated YouTube video resources for a skill and level.
    """
    skill_normalized = normalize_skill_name(skill)
    level_lower = level.lower().strip()
    
    # Direct match
    if skill_normalized in CURATED_RESOURCES:
        if level_lower in CURATED_RESOURCES[skill_normalized]:
            resources = CURATED_RESOURCES[skill_normalized][level_lower]
            return [{
                "source": "curated",
                "url_type": "direct",
                **res
            } for res in resources]
    
    # Partial match
    for curated_skill, levels in CURATED_RESOURCES.items():
        if curated_skill in skill_normalized or skill_normalized in curated_skill:
            if level_lower in levels:
                resources = levels[level_lower]
                return [{
                    "source": "curated",
                    "url_type": "direct",
                    **res
                } for res in resources]
    
    return []


def get_generic_direct_resources(level: str) -> List[Dict[str, Any]]:
    """
    Get generic YouTube resources for unknown skills.
    """
    level_lower = level.lower().strip()
    resources = GENERIC_DIRECT_RESOURCES.get(level_lower, GENERIC_DIRECT_RESOURCES["beginner"])
    return [{
        "source": "generic_curated",
        "url_type": "direct",
        **res
    } for res in resources]


def get_all_curated_for_matching(skill: str, level: str) -> List[Dict[str, Any]]:
    """
    Get all curated resources for potential matching with Gemini suggestions.
    """
    skill_normalized = normalize_skill_name(skill)
    level_lower = level.lower().strip()
    all_resources = []
    
    # Get primary level
    primary = get_curated_resources(skill, level)
    all_resources.extend(primary)
    
    # Get adjacent levels for broader matching
    if skill_normalized in CURATED_RESOURCES:
        for lvl, resources in CURATED_RESOURCES[skill_normalized].items():
            if lvl != level_lower:
                for res in resources:
                    all_resources.append({
                        "source": "curated",
                        "url_type": "direct",
                        "adjacent_level": True,
                        **res
                    })
    
    return all_resources


def get_level_modifiers(level: str) -> List[str]:
    """Get query modifier keywords for a level."""
    return LEVEL_MODIFIERS.get(level.lower(), LEVEL_MODIFIERS["beginner"])
