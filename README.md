# Canvas course builder
A semi-automated Canvas course builder. 

## Getting started
```
# Install all dependencies
pipenv install --three

# Build a course using config files from db-testing 
pipenv run python build_course.py -c ./data/db-testing -d -m

# Help
pipenv run python build_course.py -h
```

## Configuration files
`./etc`: Canvas API_URL and API_KEY
`./data` contains following configuration files for building a course:  
- `course_config.json`: contains course setup configurations; e.g., date, module structure, grading scheme, etc.  
- `course_var.json`: course variables that have no API; update required for each course; question bank and rubric;   
- `course_content.json`: contains title and url of content  

---

## Build a course from scratch
### Create course page
1. Go to the Question Bank Collection course on Canvas and follow the instructions to update the IDs of questions banks and rubrics in `course_var.json`
2. Update course details in `course_config.json` (coursenum and date)
3. Run [`build_course.py`](#getting-started)
4. Replace Assignment 3, Mock Exam and Final Exam with the imported templates from the Question Bank Collection course
5. Enable “Assignment Groups Weight”

### Update course schedule
1. Move schedule file (e.g., `./var/schedule-<>.csv`) to the content-builder folder (`../database`)
2. Knit policies file (e.g., `policies-<>.rmd`)
3. Commit and push

### Publish course page
1. Set availability for midterm and final exams
2. Lockdown browser settings
3. Correct due dates if necessary (e.g., Holiday)
4. Publish
5. Welcome announcement