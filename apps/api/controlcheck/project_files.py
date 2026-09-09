"""Microsoft Project file adapter normalized to the spreadsheet source shape."""
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


HEADERS = ['Activity ID', 'Name', 'Planned Start', 'Planned Finish', 'Actual Progress', 'Budget', 'Actual Cost', 'Task UID']


def _value(value):
    if value is None:
        return ''
    return str(value).strip()


def _date(value):
    return _value(value).split('T', 1)[0]


def normalize_tasks(tasks):
    rows = []
    for task in tasks:
        if task.get('summary'):
            continue
        uid = _value(task.get('uid'))
        name = _value(task.get('name'))
        if not uid or not name:
            continue
        rows.append({'Activity ID': uid, 'Name': name, 'Planned Start': _date(task.get('planned_start')),
                     'Planned Finish': _date(task.get('planned_finish')),
                     'Actual Progress': _value(task.get('percent_complete')),
                     'Budget': _value(task.get('budget')), 'Actual Cost': _value(task.get('actual_cost')),
                     'Task UID': uid})
    if not rows:
        raise ValueError('File project tidak berisi aktivitas yang dapat dianalisis.')
    return {'headers': HEADERS, 'rows': rows, 'sheet': 'Microsoft Project'}


def _xml_tasks(content):
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError('Microsoft Project XML tidak valid.') from exc
    tasks = []
    for task in root.findall('.//{*}Task'):
        value = lambda name: task.findtext('{*}' + name) or ''
        tasks.append({'uid': value('UID'), 'name': value('Name'), 'summary': value('Summary') == '1',
                      'planned_start': value('BaselineStart') or value('Start'),
                      'planned_finish': value('BaselineFinish') or value('Finish'),
                      'percent_complete': value('PercentComplete'), 'budget': value('BaselineCost') or value('Cost'),
                      'actual_cost': value('ActualCost')})
    return tasks


def _mpp_tasks(content):
    try:
        import jpype
        import mpxj  # noqa: F401 -- configures MPXJ jars on the JVM classpath
        if not jpype.isJVMStarted():
            java_home = os.getenv('CONTROLCHECK_JAVA_HOME')
            jvm = os.path.join(java_home, 'bin', 'server', 'jvm.dll') if java_home else None
            jpype.startJVM(jvm, convertStrings=True)
        from org.mpxj.reader import UniversalProjectReader
    except Exception as exc:
        raise ValueError('Parser MPP belum tersedia di server.') from exc
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.mpp', delete=False) as stream:
            stream.write(content)
            path = stream.name
        project = UniversalProjectReader().read(path)
        tasks = []
        for task in project.getTasks():
            tasks.append({'uid': task.getUniqueID(), 'name': task.getName(), 'summary': bool(task.getSummary()),
                          'planned_start': task.getBaselineStart() or task.getStart(),
                          'planned_finish': task.getBaselineFinish() or task.getFinish(),
                          'percent_complete': task.getPercentageComplete(),
                          'budget': task.getBaselineCost() or task.getCost(), 'actual_cost': task.getActualCost()})
        return tasks
    except Exception as exc:
        raise ValueError('File MPP tidak dapat dibaca. Coba ekspor Microsoft Project XML.') from exc
    finally:
        if path and os.path.exists(path):
            os.unlink(path)


def read_project_file(filename, content):
    extension = Path(filename).suffix.lower()
    if extension == '.mpp':
        result = normalize_tasks(_mpp_tasks(content))
    elif extension == '.xml':
        result = normalize_tasks(_xml_tasks(content))
    else:
        raise ValueError('Format project harus .mpp atau .xml.')
    result['filename'] = Path(filename.replace('\\', '/')).name
    return result
