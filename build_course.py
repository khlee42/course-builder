import argparse, os, sys, datetime, json
from configparser import ConfigParser
from contextlib import contextmanager
from pathlib import Path

import pandas as pd
from canvasapi.canvas import Canvas
from tqdm import tqdm


def build_course(var_path='./var'):
    '''Canvas course provision with configuration files
        
        build_course.py -h for help

        Configuration files:
            course_config.json: contains course setup configurations; e.g., date, module structure, grading scheme, etc.
            course_var.json: course variables that have no API; update required for each course; question bank and rubric; 
            course_content.json: contains title and url of content
    '''

    args = argparser()

    create_canvas_module = args.module
    config_folder = Path(args.config)

    with open(config_folder / 'course_var.json') as f:
        var = json.load(f)
    with open(config_folder / 'course_content.json') as f:
        content = json.load(f)
    with open(config_folder / 'course_config.json') as f:
        config = json.load(f)
    
    cred = get_config('CANVAS')
    cv = Canvas(*cred.values())
    course = cv.get_course(config['coursenum'])

    if args.delete:
        print('Cleaning up for provision')
        clean_course(course)

    print('Updating course setting')
    grading_stardard_id = course.add_grading_standards(title=config['grading_scheme'], grading_scheme_entry=config[config['grading_scheme']]).id
    course.update(
        course = {
            'name': config['coursetitle'],
            'syllabus_body': iframe_patcher(config['syllabus']),
            'image_url': config['image_url'],
            'grading_standard_enabled': True,
            'grading_standard_id': grading_stardard_id
        }
    )
    for tab in course.get_tabs():
        if tab.id!="home" and tab.id!="settings":
            if tab.id in config['tabs']:
                tab.update(hidden=False)
            else:
                tab.update(hidden=True)

    calendar, off_day = gen_calendar(config['date'])

    format = config['date']['format']
    assignment_groups, modules = get_course_format(format, config)

    print('Creating assignment groups')
    groups = {group: course.create_assignment_group(**group_dict).id for group, group_dict in assignment_groups.items()}

    row=[]  # for schedule table
    for week_idx, module_dict in modules.items():
        module_start_date = calendar[int(week_idx)]

        if create_canvas_module:
            if is_after_offday(module_start_date, off_day):
                course.create_module({'name': "Holiday - No Class", 'unlock_at': off_day}) 
            module_dict['module']['unlock_at'] = module_start_date
            new_module = course.create_module(module_dict['module'])

        for item in tqdm(module_dict['items'], desc=f"Creating contents - {module_dict['module']['name']}"):
            # create content items
            prefix = item[0]
            item_type = get_item_type(prefix)
            unique_config = content[item_type][item]
            default_config = find_config_dict(item, config['setting'])
            item_dict = combine_config(unique_config, default_config)

            content_id = create_content_wrapper(course, item_type, item_dict, module_start_date, groups, var)

            if item in var['rubric']:
                add_rubric(course, var['rubric'][item], content_id)

            if create_canvas_module:
                module_item_dict = get_module_item_dict(item_type, content_id)    
                new_module.create_module_item(module_item_dict)
            
            row.append([module_start_date, list(unique_config.values())[0]])

    rows = pd.DataFrame(row, columns = ['Date', 'Topics'])
    cnum = config_folder.stem.split('-')[1]
    Path(var_path).mkdir(parents=True, exist_ok=True)
    rows.to_csv(f'{var_path}/schedule-{cnum}.csv', index=False)

@contextmanager
def ignored(*exceptions):
  try:
    yield
  except exceptions:
    pass 


def get_course_format(format, config):
    if format==6:
        return config['assignment_groups_6week'], config['modules_6week']
    elif format==11:
        return config['assignment_groups_11week'], config['modules_11week']
    elif format==15:
        return config['assignment_groups_11week'], config['modules_15week']


def after_nweeks(start, nweeks, offday):
    nweeks -= 1
    date = start + datetime.timedelta(weeks=nweeks)
    if date>=offday:
        return date + datetime.timedelta(weeks=1)
    return date


def convert_to_date(date):
    return datetime.datetime.strptime(date, '%Y-%m-%d')


def gen_calendar(date_dict):
    start_day = convert_to_date(date_dict['start_day'])
    off_day = convert_to_date(date_dict['off_day'])
    nweeks = date_dict['format']    # add one for final
    # nweeks = date_dict['format'] + 1    # add one for final

    return {week_idx: after_nweeks(start_day, week_idx, off_day) for week_idx in range(1, nweeks+1)}, off_day


def is_after_offday(start_day, off_day):
    if start_day == off_day + datetime.timedelta(days=7):
        return True
    return False


def gen_duedate(start_date, due):
    due_in = datetime.timedelta(days=due)
    midnight = datetime.time(23,59)
    return datetime.datetime.combine(start_date + due_in, midnight)


def iframe_patcher(url, width=1200, height=1200):
    return f'<iframe src=\"{url}\" width=\"{width}\" height=\"{height}\"></iframe>'


def clean_course(course):
    for group in course.get_assignment_groups():
        group.delete()
    for quiz in course.get_quizzes():
        quiz.delete()
    for page in course.get_pages():
        page.delete()
    for module in course.get_modules():
        module.delete()
    for asgmt in course.get_assignments():
        asgmt.delete()
    for discussion in course.get_discussion_topics():
        discussion.delete()


def create_page(course, page, page_config={}):
    page['body'] = iframe_patcher(page['body'])
    new_page = course.create_page(wiki_page=page|page_config)
    return new_page.url


def dict_update(dict, start_date, groups):  
    with ignored(KeyError):
        dict['description'] = iframe_patcher(dict['description'], height=600) # custom height for quiz
        dict['assignment_group_id'] = groups[dict['assignment_group_id']]
        dict['due_at'] = gen_duedate(start_date, dict['due'])
        dict['unlock_at'] = convert_to_date(dict['unlock_at'])
        dict['lock_at'] = gen_duedate(dict['unlock_at'], dict['due'])
    return dict


def create_assignment(course, asgmt, start_date, groups):
    asgmt = dict_update(asgmt, start_date, groups)
    new_assignment = course.create_assignment(asgmt)
    return new_assignment.id


def create_quiz(course, quiz, start_date, groups, var):
    quiz = dict_update(quiz, start_date, groups)
    new_quiz = course.create_quiz(quiz)

    for question_group in quiz['question_group']:
        question_group['assessment_question_bank_id'] = var['question_bank'][question_group['assessment_question_bank_id']]
        new_quiz.create_question_group([question_group])

    return new_quiz.id

def create_discussion(course, topic, topic_config={}):
    new_discussion = course.create_discussion_topic(**topic)
    return new_discussion.id

def create_content_wrapper(course, content_type, content_dict, start_date, groups, var):
    if content_type=='Page':
        return create_page(course, content_dict)
    elif content_type=='Assignment':
        return create_assignment(course, content_dict, start_date, groups)
    elif content_type=='Quiz':
        return create_quiz(course, content_dict, start_date, groups, var)
    elif content_type=='Discussion':
        return create_discussion(course, content_dict)
    else:
        raise Exception(f'{content_type} is an invalid content_type.')


def get_item_type(prefix):
    if prefix=='p':
        return 'Page'
    elif prefix=='a':
        return 'Assignment'
    elif prefix=='q':
        return 'Quiz'
    elif prefix=='d':
        return 'Discussion'
    return None


def get_module_item_dict(item_type, content_id):
    if item_type=='Page':
        return {'type': item_type, 'page_url': content_id}
    else:
        return {'type': item_type, 'content_id': content_id}


def find_config_dict(item, configs):
    for l in configs:
        if item in l['target']:
            return l['config']


def combine_config(unique, default):
    if default is not None:
        '''Add only configs undefined in unique; unique supercedes default'''
        configs_undefined = default.keys() - unique.keys()
        configs_to_add = {config:default[config] for config in configs_undefined}
        return unique | configs_to_add
    else:
        return unique


def add_rubric(course, rubric_id, content_id):
    rubric_association = {
        'rubric_id': rubric_id, 
        'association_id': content_id, 
        'use_for_grading': True, 
        'association_type': 'Assignment',
        'purpose': "grading"
    }
    course.create_rubric_association(rubric_association=rubric_association)


def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Config folder; e.g., -c \'./data/db-testing\'', metavar='')
    parser.add_argument('-d', '--delete', help='Delete all existing data; default is false', action='store_true')
    parser.add_argument('-m', '--module', help='Create canvas modules; default is false', action='store_true')
    args = parser.parse_args()
    
    # # temp for debugging
    # args.config = Path('./data/db-testing')  
    # args.module = True
    # args.delete = True

    if args.config is None:
        os.system(f'python {os.path.basename(__file__)} -h')
        sys.exit(f'Arguments not provided')
    
    return args


def get_config(section, filename='etc/config.ini'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)
 
    # get section, default to postgresql
    db = {}
    
    # Checks to see if section (postgresql) parser exists
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
         
    # Returns an error if a parameter is called that is not listed in the initialization file
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))
 
    return db


if __name__=='__main__':
    build_course()