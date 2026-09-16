"""Microsoft Project file adapter normalized to the spreadsheet source shape."""
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


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


def _is_jvm_available():
    """Check whether a valid Java Virtual Machine is available without risking access violations."""
    try:
        import jpype  # type: ignore
        if jpype.isJVMStarted():
            return True
        java_home = os.getenv('CONTROLCHECK_JAVA_HOME') or os.getenv('JAVA_HOME')
        if not java_home or not os.path.isdir(java_home):
            return False
        jvm_dll = os.path.join(java_home, 'bin', 'server', 'jvm.dll')
        if os.path.exists(jvm_dll):
            return True
        for lib in ['libjvm.so', 'libjvm.dylib']:
            for root, _, files in os.walk(java_home):
                if lib in files:
                    return True
        return False
    except Exception:
        return False


def _xer_tasks_tabular(content):
    """Read core P6 tables (TASK, TASKPRED, CALENDAR, PROJWBS, PROJECT) directly without JVM."""
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            text = content.decode('cp1252')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin1')
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

    # Index calendars: clndr_id -> clndr_name
    calendars = {}
    for record in tables.get('CALENDAR', []):
        cid = _value(record.get('clndr_id'))
        cname = _value(record.get('clndr_name'))
        if cid and cname:
            calendars[cid] = cname

    # Index WBS: wbs_id -> wbs_name / wbs_short_name
    wbs_map = {}
    for record in tables.get('PROJWBS', []):
        wid = _value(record.get('wbs_id'))
        wname = _value(record.get('wbs_name') or record.get('wbs_short_name'))
        if wid and wname:
            wbs_map[wid] = wname

    # Index Predecessors: task_id -> list of pred_task_id
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
        clndr_id = _value(record.get('clndr_id'))
        calendar_name = calendars.get(clndr_id) or _value(record.get('calendar')) or None

        target_start = record.get('target_start_date')
        target_end = record.get('target_end_date')
        restart_date = record.get('restart_date')
        reend_date = record.get('reend_date')
        early_start = record.get('early_start_date')
        early_end = record.get('early_end_date')
        act_start = record.get('act_start_date')
        act_end = record.get('act_end_date')

        planned_start = _date(target_start or restart_date or early_start or act_start)
        planned_finish = _date(target_end or reend_date or early_end or act_end)

        tasks.append({
            'uid': uid,
            'activity_id': _value(record.get('task_code') or record.get('activity_id') or uid),
            'name': name,
            'summary': task_type in ('TT_WBS', 'WBS') or bool(record.get('summary')),
            'planned_start': planned_start,
            'planned_finish': planned_finish,
            'baseline_start': _date(target_start),
            'baseline_finish': _date(target_end),
            'percent_complete': record.get('phys_complete_pct') or record.get('complete_pct'),
            'budget': record.get('target_cost') or record.get('budget'),
            'actual_cost': record.get('act_cost') or record.get('actual_cost'),
            'critical': _value(record.get('critical_flag')).upper() in ('Y', '1', 'TRUE'),
            'milestone': task_type in ('TT_MILE', 'MILESTONE', 'TT_FINMILE', 'TT_STARTMILE') or _value(record.get('milestone_flag')).upper() in ('Y', '1'),
            'total_slack': record.get('total_float_hr_cnt') or record.get('total_slack'),
            'calendar': calendar_name,
            'constraint_type': _value(record.get('cstr_type') or record.get('constraint_type')) or None,
            'constraint_date': _date(record.get('cstr_date') or record.get('constraint_date')) or None,
            'predecessor_uids': predecessors.get(uid, []),
        })
    if not tasks:
        raise ValueError('File XER tidak berisi aktivitas yang dapat dianalisis.')
    return tasks


def normalize_tasks(tasks: list[dict[str, Any]]) -> dict[str, Any]:
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
    if not _is_jvm_available():
        raise ValueError('Parser MPP belum tersedia di server.')
    path = None
    try:
        import jpype  # type: ignore
        import mpxj  # type: ignore  # noqa: F401 -- configures MPXJ jars on the JVM classpath
        if not jpype.isJVMStarted():
            java_home = os.getenv('CONTROLCHECK_JAVA_HOME') or os.getenv('JAVA_HOME')
            jvm = os.path.join(java_home, 'bin', 'server', 'jvm.dll') if java_home else None
            if jvm:
                jpype.startJVM(jvm, convertStrings=True)
            else:
                jpype.startJVM(convertStrings=True)
        from org.mpxj.reader import UniversalProjectReader  # type: ignore
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
    # Native-First: Fast, deterministic, pure Python, and zero JVM crash risk
    native_error = None
    try:
        return _xer_tasks_tabular(content)
    except Exception as exc:
        native_error = exc

    # Optional fallback to MPXJ only if JVM environment is confirmed ready
    if _is_jvm_available():
        try:
            import jpype  # type: ignore
            import mpxj  # type: ignore  # noqa: F401 -- configures MPXJ jars on the JVM classpath
            if not jpype.isJVMStarted():
                java_home = os.getenv('CONTROLCHECK_JAVA_HOME') or os.getenv('JAVA_HOME')
                jvm = os.path.join(java_home, 'bin', 'server', 'jvm.dll') if java_home else None
                if jvm:
                    jpype.startJVM(jvm, convertStrings=True)
                else:
                    jpype.startJVM(convertStrings=True)
            from org.mpxj.primavera import PrimaveraXERFileReader  # type: ignore
            path = None
            try:
                with tempfile.NamedTemporaryFile(suffix='.xer', delete=False) as stream:
                    stream.write(content)
                    path = stream.name
                project = PrimaveraXERFileReader().read(path)
                if project is None:
                    raise ValueError('MPXJ tidak menghasilkan project file.')
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
            finally:
                _remove_temp_file(path)
        except Exception:
            pass

    raise ValueError(f'File Primavera P6 XER tidak dapat dibaca ({native_error}). Pastikan file valid atau pasang Java 17 dan MPXJ.')


def read_project_file(filename: str, content: bytes) -> dict[str, Any]:
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

