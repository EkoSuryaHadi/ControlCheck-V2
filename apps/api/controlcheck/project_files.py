"""Microsoft Project file adapter normalized to the spreadsheet source shape."""
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


HEADERS = ['Activity ID', 'Name', 'Planned Start', 'Planned Finish', 'Actual Progress', 'Budget', 'Actual Cost', 'Task UID', 'Is Critical', 'Is Milestone', 'Total Slack', 'Predecessor IDs', 'Calendar', 'Constraint Type', 'Constraint Date', 'Baseline Start', 'Baseline Finish']


def _remove_temp_file(path):
    """Do not replace a parser result when MPXJ still holds a Windows temp file."""
    if not path or not os.path.exists(path):
        return
    try:
        os.unlink(path)
    except PermissionError:
        pass


def _value(value):
    if value is None:
        return ''
    return str(value).strip()


def _date(value):
    return _value(value).replace('T', ' ', 1).split(' ', 1)[0]


def _duration_number(value):
    """Return MPXJ duration magnitudes without their display unit."""
    text = _value(value)
    match = re.fullmatch(r'([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*[A-Za-z]+', text)
    return match.group(1) if match else text


def _predecessor_task(relation):
    current = getattr(relation, 'getPredecessorTask', None)
    return current() if current else relation.getSourceTask()


def _xer_tasks_tabular(content):
    """Read core P6 TASK/TASKPRED tables when a Java reader rejects a variant export."""
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            text = content.decode('cp1252')
        except UnicodeDecodeError as exc:
            raise ValueError('Encoding XER tidak didukung.') from exc
    tables = {}
    current = None
    headers = None
    for line in text.splitlines():
        if not line:
            continue
        cells = line.split('\t')
        marker = cells[0]
        if marker == '%T':
            current = cells[1].strip() if len(cells) > 1 else None
            headers = None
            continue
        if marker == '%F' and current:
            headers = [item.strip() for item in cells[1:]]
            tables[current] = []
            continue
        if marker == '%R' and current and headers:
            values = cells[1:] + [''] * max(0, len(headers) - len(cells) + 1)
            tables[current].append(dict(zip(headers, values[:len(headers)])))
    task_records = tables.get('TASK', [])
    if not task_records:
        raise ValueError('File XER tidak berisi tabel TASK yang dapat dianalisis.')
    predecessors = {}
    for record in tables.get('TASKPRED', []):
        task_id = _value(record.get('task_id'))
        pred_id = _value(record.get('pred_task_id') or record.get('pred_taskid'))
        if task_id and pred_id:
            predecessors.setdefault(task_id, []).append(pred_id)
    tasks = []
    for record in task_records:
        uid = _value(record.get('task_id') or record.get('uid'))
        name = _value(record.get('task_name') or record.get('name'))
        if not uid or not name:
            continue
        task_type = _value(record.get('task_type')).upper()
        tasks.append({
            'uid': uid, 'activity_id': _value(record.get('task_code') or record.get('activity_id') or uid),
            'name': name, 'planned_start': _date(record.get('target_start_date') or record.get('early_start_date')),
            'planned_finish': _date(record.get('target_end_date') or record.get('early_end_date')),
            'percent_complete': record.get('phys_complete_pct') or record.get('complete_pct'),
            'budget': record.get('target_cost') or record.get('budget'),
            'actual_cost': record.get('act_cost') or record.get('actual_cost'),
            'critical': _value(record.get('critical_flag')).upper() in ('Y', '1', 'TRUE'),
            'milestone': task_type in ('TT_MILE', 'MILESTONE') or _value(record.get('milestone_flag')).upper() in ('Y', '1'),
            'total_slack': record.get('total_float_hr_cnt') or record.get('total_slack'),
            'predecessor_uids': predecessors.get(uid, []),
        })
    if not tasks:
        raise ValueError('File XER tidak berisi aktivitas yang dapat dianalisis.')
    return tasks


def normalize_tasks(tasks):
    usable = [task for task in tasks if not task.get('summary') and _value(task.get('name'))]
    activity_ids = {
        _value(task.get('uid')): _value(task.get('activity_id')) or _value(task.get('uid'))
        for task in usable if _value(task.get('uid'))
    }
    rows = []
    for task in usable:
        uid = _value(task.get('uid'))
        activity_id = _value(task.get('activity_id')) or uid
        if not activity_id:
            continue
        predecessor_values = task.get('predecessor_uids', task.get('predecessor_ids', [])) or []
        predecessors = [activity_ids.get(_value(value), _value(value)) for value in predecessor_values if _value(value)]
        rows.append({
            'Activity ID': activity_id, 'Name': _value(task.get('name')),
            'Planned Start': _date(task.get('planned_start') or task.get('baseline_start')),
            'Planned Finish': _date(task.get('planned_finish') or task.get('baseline_finish')),
            'Actual Progress': _value(task.get('percent_complete')),
            'Budget': _value(task.get('budget')), 'Actual Cost': _value(task.get('actual_cost')),
            'Task UID': uid, 'Is Critical': str(bool(task.get('critical'))).lower(),
            'Is Milestone': str(bool(task.get('milestone'))).lower(),
            'Total Slack': _duration_number(task.get('total_slack')),
            'Predecessor IDs': ';'.join(predecessors), 'Calendar': _value(task.get('calendar')),
            'Constraint Type': _value(task.get('constraint_type')), 'Constraint Date': _date(task.get('constraint_date')),
            'Baseline Start': _date(task.get('baseline_start')), 'Baseline Finish': _date(task.get('baseline_finish')),
        })
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
                      'actual_cost': value('ActualCost'), 'critical': value('Critical') == '1',
                      'milestone': value('Milestone') == '1', 'total_slack': value('TotalSlack'),
                      'predecessor_ids': [link.findtext('{*}PredecessorUID') for link in task.findall('{*}PredecessorLink')]})
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
                          'budget': task.getBaselineCost() or task.getCost(), 'actual_cost': task.getActualCost(),
                          'critical': bool(task.getCritical()), 'milestone': bool(task.getMilestone()),
                          'total_slack': task.getTotalSlack(),
                          'predecessor_ids': [_predecessor_task(relation).getUniqueID()
                                              for relation in task.getPredecessors()
                                              if _predecessor_task(relation) is not None]})
        return tasks
    except Exception as exc:
        raise ValueError('File MPP tidak dapat dibaca. Coba ekspor Microsoft Project XML.') from exc
    finally:
        _remove_temp_file(path)



def _xer_tasks(content):
    try:
        import jpype
        import mpxj  # noqa: F401 -- configures MPXJ jars on the JVM classpath
        if not jpype.isJVMStarted():
            java_home = os.getenv('CONTROLCHECK_JAVA_HOME')
            jvm = os.path.join(java_home, 'bin', 'server', 'jvm.dll') if java_home else None
            jpype.startJVM(jvm, convertStrings=True)
        from org.mpxj.primavera import PrimaveraXERFileReader
    except Exception as exc:
        raise ValueError('Parser XER belum tersedia di server. Pastikan Java 17 dan MPXJ tersedia.') from exc
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.xer', delete=False) as stream:
            stream.write(content)
            path = stream.name
        try:
            project = PrimaveraXERFileReader().read(path)
            if project is None:
                raise ValueError('MPXJ tidak menghasilkan project file.')
        except Exception:
            return _xer_tasks_tabular(content)
        tasks = []
        for task in project.getTasks():
            calendar = task.getCalendar()
            source_tasks = [_predecessor_task(relation) for relation in task.getPredecessors()]
            tasks.append({
                'uid': task.getUniqueID(), 'activity_id': task.getActivityID(), 'name': task.getName(),
                'summary': bool(task.getSummary()), 'planned_start': task.getBaselineStart() or task.getStart(),
                'planned_finish': task.getBaselineFinish() or task.getFinish(),
                'baseline_start': task.getBaselineStart(), 'baseline_finish': task.getBaselineFinish(),
                'percent_complete': task.getPercentageComplete(), 'budget': task.getBaselineCost() or task.getCost(),
                'actual_cost': task.getActualCost(), 'critical': bool(task.getCritical()),
                'milestone': bool(task.getMilestone()), 'total_slack': task.getTotalSlack(),
                'calendar': calendar.getName() if calendar is not None else None,
                'constraint_type': task.getConstraintType(), 'constraint_date': task.getConstraintDate(),
                'predecessor_uids': [source.getUniqueID() for source in source_tasks if source is not None],
            })
        return tasks
    except Exception as exc:
        raise ValueError('File Primavera P6 XER tidak dapat dibaca.') from exc
    finally:
        _remove_temp_file(path)

def read_project_file(filename, content):
    extension = Path(filename).suffix.lower()
    if extension == '.mpp':
        result = normalize_tasks(_mpp_tasks(content))
    elif extension == '.xml':
        result = normalize_tasks(_xml_tasks(content))
    elif extension == '.xer':
        result = normalize_tasks(_xer_tasks(content))
        result['sheet'] = 'Primavera P6'
    else:
        raise ValueError('Format project harus .mpp, .xml, atau .xer.')
    result['filename'] = Path(filename.replace('\\', '/')).name
    return result
