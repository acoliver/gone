"""Sofa SAT policy: changed surfaces cannot inherit fitted rigid crossings."""
RIGID = frozenset({'Frame', 'Feet', 'Rivets'})


def rigid_counts(report):
    names = sorted(RIGID)
    counts = {'self/'+name: report['self'][name]['count'] for name in names}
    counts.update({a+'/'+b: report['pairs'].get(a+'/'+b, {'count': 0})['count']
                   for i, a in enumerate(names) for b in names[i+1:]})
    return counts


def sofa_contacts(report, unaged):
    baseline, actual = rigid_counts(unaged), rigid_counts(report)
    changed_self = sum(v['count'] for n, v in report['self'].items() if n not in RIGID)
    changed_pairs = sum(v['count'] for n, v in report['pairs'].items()
                        if not set(n.split('/')).issubset(RIGID))
    return {'changed_intersections': changed_self+changed_pairs,
            'rigid_baseline': baseline, 'rigid_actual': actual,
            'rigid_baseline_unchanged': actual == baseline,
            'pass': changed_self+changed_pairs == 0 and actual == baseline}
