# Canvas Course Builder
A semi-automated course builder for Canvas which creates course content and schedule as provided in the configuration files (`.json`). Some features need manual control as they have no public-facing APIs (e.g., question banks).

## Prerequisites
* The config files only contain links to the contents, which are published in [the content-builder repo](https://github.com/khlee42/database).  
* Install dependencies
```
pipenv install --three
```

## Configuration files
`./etc`: Canvas API_URL and API_KEY  
`./data` contains following configuration files for building a course:  
- `course_config.json`: course setup configurations; e.g., date, module structure, grading scheme, etc.  
- `course_var.json`: course variables for features with no APIs; update required for each course   
- `course_content.json`: title and url of content  

## Usage
### Create course page
1. Import the questions banks and rubrics from [Question Bank Collection course](https://canvas.wayne.edu/courses/74658)
2. Update the questions banks and rubrics **IDs** in `course_var.json`
3. Update course details in `course_config.json` (coursenum and date)
4. Run `build_course.py`
```
# Build a course using config files from db-testing 
pipenv run python build_course.py -c ./data/db-testing -d -m

# Help
pipenv run python build_course.py -h
```
4. Import the quizzes (Assignment 3, Mock Exam and Final Exam) from [Question Bank Collection course](https://canvas.wayne.edu/courses/74658) and replace the existing ones with them 
* These quizzes must be imported manually because the questions in the quizzes must be in a pre-defined order but the API always shuffle the order of the questions
* Update the details if necessary (e.g., due date)
* Move them to the correct assignment groups and week modules
* Enable “Assignment Groups Weight” in the Assignments tab

### Update course schedule
1. Move schedule file (e.g., `./var/schedule-<>.csv`) to the content-builder folder (`../database`)
2. Knit policies file (e.g., `policies-<>.rmd`)
3. Commit and push

### Before publish course page
1. Set availability for midterm and final exams
2. Check lockdown browser settings
3. Adjust due dates if necessary (e.g., Holiday)
4. Publish
5. Welcome announcement

### During semester
1. Create Oracle accounts for students
2. Update schema access privileges (JUSTLEE, SRECORD, CITYJAIL, FINALEXAM)
3. Get approved for Datacamp access and update the link in the course page
