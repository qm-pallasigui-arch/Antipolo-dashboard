"""Reporting-calendar derivation.

The DOH guideline on plotting the annual morbidity week calendar adopts the CDC
MMWR convention: week 1 is the first week of the year with at least four days in
the calendar year, and weeks begin on Sunday. The rule is arithmetic, so a
year's length is derived from the year rather than asserted by an operator.

Both boundaries use the four-day rule. The week containing January 1 is week 1
only if at least four of its days fall in the new year; symmetrically, the last
week counted for the year must also contribute at least four days, so trailing
days belong to the following year's week 1.
"""
import datetime as dt

RULE = ('CDC MMWR: week 1 is the first week with at least four days in the year; '
        'weeks begin on Sunday.')


def _sunday_on_or_before(date):
    """Weekday() is Monday=0..Sunday=6, so this is the Sunday starting the week."""
    return date - dt.timedelta(days=(date.weekday() + 1) % 7)


def first_week_start(year):
    """Sunday that begins morbidity week 1 of the reporting year.

    The same four-day rule year_length applies, factored out so a derived week
    count and a derived week date can never disagree about where the year starts.
    """
    january = dt.date(year, 1, 1)
    first = _sunday_on_or_before(january)
    if 7 - (january - first).days < 4:
        first += dt.timedelta(7)
    return first


def week_start(year, week):
    """Sunday that begins the given morbidity week of a reporting year.

    Weeks are seven days apart and week 1 is first_week_start, so this is the
    other half of the MMWR derivation the calendar already performs. It lets
    monthly and quarterly summaries be grouped without a source date column,
    which the workbook does not carry.

    Derived from the reporting week number, not from the source. A summary built
    on it states that, because it is not a source-established date.
    """
    if week < 1:
        raise ValueError('Reporting weeks start at 1.')
    return first_week_start(year) + dt.timedelta(weeks=week - 1)


def year_length(year):
    """Number of morbidity weeks in a reporting year under the MMWR rule."""
    december = dt.date(year, 12, 31)
    first = first_week_start(year)
    last = _sunday_on_or_before(december)
    if (december - last).days + 1 < 4:
        last -= dt.timedelta(7)
    return (last - first).days // 7 + 1


def derive(years):
    """Map reporting years to derived week counts, keyed as strings for metadata."""
    return {str(year): year_length(int(year)) for year in sorted(set(years))}


def has_week_three(records, lengths):
    """Record indices supplying a nonzero week 53 in a year derived as 52 weeks.

    These are the cells where the source and the derived calendar disagree about
    whether the week existed, and the operator decides rather than the application
    guessing. A zero count is excluded here: nothing is lost by dropping it.
    """
    conflicts = []
    for index, row in enumerate(records):
        if int(row.get('morbidity_week') or 0) != 53:
            continue
        count = row.get('case_count')
        if count is None or float(count) == 0:
            continue
        if lengths.get(str(int(row['year']))) == 52:
            conflicts.append(index)
    return conflicts