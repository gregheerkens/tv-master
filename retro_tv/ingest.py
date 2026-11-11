"""Required source context and explicitly estimated continuity reuse defaults."""
import calendar
import json
import re
from datetime import date, timedelta
from pathlib import Path

HOLIDAYS = ('new_years_day','martin_luther_king_jr_day','presidents_day',
            'valentines_day','st_patricks_day','easter','memorial_day','juneteenth',
            'independence_day','labor_day','halloween','veterans_day','thanksgiving','christmas')
MEDIA_EXTENSIONS={'.mp4','.mkv','.avi','.mov','.m4v','.mpg','.mpeg','.ts','.m2ts','.vob','.webm'}


def date_bracket(value):
    if not isinstance(value,str):
        raise ValueError('recorded_date must be YYYY, YYYY-MM or YYYY-MM-DD')
    if re.fullmatch(r'\d{4}',value):
        year=int(value)
        return date(year,1,1),date(year+1,1,1),'year'
    if re.fullmatch(r'\d{4}-\d{2}',value):
        first=date.fromisoformat(value+'-01')
        last=first+timedelta(days=calendar.monthrange(first.year,first.month)[1])
        return first,last,'month'
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        first=date.fromisoformat(value)
        return first,first+timedelta(days=1),'day'
    raise ValueError('recorded_date must be YYYY, YYYY-MM or YYYY-MM-DD')


def validate_context(value, *, allow_legacy=False):
    if not isinstance(value,dict):
        raise ValueError('each source requires an ingest object identifying ripped or recorded media')
    value=dict(value)
    kind=value.get('kind')
    if kind in ('ripped','generated') or (allow_legacy and kind=='legacy_unknown'):
        return value
    if kind!='recorded':
        raise ValueError('source ingest kind must be ripped or recorded')
    first,last,precision=date_bracket(value.get('recorded_date'))
    if type(value.get('seasonal')) is not bool:
        raise ValueError('recorded media requires an explicit seasonal true/false answer')
    if value['seasonal']:
        if value.get('holiday') not in HOLIDAYS:
            raise ValueError('seasonal recordings require a supported American holiday')
        year=value.get('holiday_year')
        if type(year) is not int or not first.year-1<=year<=(last-timedelta(days=1)).year+1:
            raise ValueError('holiday_year must identify a year adjacent to the recording date')
        holiday_date(value['holiday'],year)
    elif value.get('holiday') is not None or value.get('holiday_year') is not None:
        raise ValueError('nonseasonal recordings must not specify a holiday')
    value.update(recorded_from=first.isoformat(),recorded_until=last.isoformat(),
                 date_precision=precision)
    return value


def nth_weekday(year,month,weekday,n):
    first=date(year,month,1)
    return first+timedelta(days=(weekday-first.weekday())%7+7*(n-1))


def holiday_date(holiday,year):
    fixed={'new_years_day':(1,1),'valentines_day':(2,14),'st_patricks_day':(3,17),
           'juneteenth':(6,19),'independence_day':(7,4),'halloween':(10,31),
           'veterans_day':(11,11),'christmas':(12,25)}
    if holiday in fixed:return date(year,*fixed[holiday])
    if holiday=='thanksgiving':return nth_weekday(year,11,3,4)
    if holiday=='labor_day':return nth_weekday(year,9,0,1)
    if holiday=='martin_luther_king_jr_day':return nth_weekday(year,1,0,3)
    if holiday=='presidents_day':return nth_weekday(year,2,0,3)
    if holiday=='memorial_day':
        last=date(year,5,31)
        return last-timedelta(days=last.weekday())
    if holiday=='easter':
        # Gregorian computus; used as a calendar anchor, never an inferred airdate.
        a=year%19;b=year//100;c=year%100;d=b//4;e=b%4;f=(b+8)//25
        g=(b-f+1)//3;h=(19*a+b-d-g+15)%30;i=c//4;k=c%4
        l=(32+2*e+2*i-h-k)%7;m=(a+11*h+22*l)//451
        month=(h+l-7*m+114)//31;day=(h+l-7*m+114)%31+1
        return date(year,month,day)
    raise ValueError('unsupported holiday')


def reuse_rule(context,kind,overrides=None):
    context=validate_context(context,allow_legacy=True)
    overrides={} if overrides is None else dict(overrides)
    if context['kind']!='recorded' or kind not in ('commercial','bumper','promo','station_id','psa'):
        return None
    first=date.fromisoformat(context['recorded_from'])
    last=date.fromisoformat(context['recorded_until'])-timedelta(days=1)
    lower=date(max(1,first.year-2),1,1)
    upper=date(min(9999,last.year+3),1,1)
    estimated=True
    if 'valid_from' in overrides or 'valid_until' in overrides:
        if not overrides.get('evidence') or not all(k in overrides for k in ('valid_from','valid_until')):
            raise ValueError('overriding a reuse bracket requires both dates and evidence')
        lower=date.fromisoformat(overrides['valid_from']);upper=date.fromisoformat(overrides['valid_until'])
        estimated=False
    if 'year_specific' in overrides:
        year=overrides['year_specific']
        if type(year) is not int or not 1<=year<=9998 or not overrides.get('evidence'):
            raise ValueError('year-specific campaigns require a valid year and evidence')
        lower=max(lower,date(year,1,1));upper=min(upper,date(year+1,1,1));estimated=False
    seasonal=overrides.get('seasonal',context['seasonal'])
    if type(seasonal) is not bool:
        raise ValueError('seasonal override must be boolean')
    holiday=overrides.get('holiday',context.get('holiday')) if seasonal else None
    if seasonal and holiday not in HOLIDAYS:
        raise ValueError('seasonal reuse requires a supported holiday')
    before=overrides.get('days_before',30);after=overrides.get('days_after',0)
    if any(type(v) is not int or not 0<=v<=90 for v in (before,after)):
        raise ValueError('holiday offsets must be integers from 0 through 90 days')
    if seasonal and not any(k in overrides for k in ('valid_from','valid_until','year_specific')):
        center=context.get('holiday_year',first.year)
        lower=holiday_date(holiday,max(2,center-2))-timedelta(days=before)
        upper=holiday_date(holiday,min(9998,center+2))+timedelta(days=after+1)
    if lower>=upper:
        raise ValueError('reuse evidence conflicts with the recording bracket')
    return {'valid_from':lower.isoformat(),'valid_until':upper.isoformat(),
            'evidence_state':'estimated' if estimated else 'evidence_based',
            'provenance':{'basis':'recording context ±2 calendar years' if estimated else overrides['evidence'],
                          'recorded_date':context['recorded_date'],'holiday_year':context.get('holiday_year')},
            'holiday':holiday,'days_before':before,'days_after':after}


def reuse_allowed(rule,day):
    day=date.fromisoformat(day)
    if not rule['valid_from']<=day.isoformat()<rule['valid_until']:
        return False
    if rule['holiday'] is None:return True
    # Adjacent years cover windows crossing New Year's Eve.
    for year in range(max(1,day.year-1),min(9998,day.year+1)+1):
        anchor=holiday_date(rule['holiday'],year)
        if anchor-timedelta(days=rule['days_before'])<=day<=anchor+timedelta(days=rule['days_after']):
            return True
    return False


def ingest_path(db,path,context):
    """Register sources only; identification and playout approval stay separate."""
    from .catalog import fingerprint, import_library
    context=validate_context(context)
    path=Path(path).resolve(strict=True)
    if context['kind']=='ripped':
        if not path.is_dir():raise ValueError('ripped-media ingest requires a folder')
        files=sorted(p for p in path.rglob('*') if p.is_file() and p.suffix.lower() in MEDIA_EXTENSIONS)
        if not files:raise ValueError('folder contains no supported media files')
    elif context['kind']=='recorded':
        if not path.is_file():raise ValueError('recorded-media ingest requires one file')
        files=[path]
    else:raise ValueError('interactive ingest supports ripped folders or recorded files')
    sources=[{'id':fingerprint(p)[:24],'path':str(p),'ingest':context,
              'provenance':{'origin':'user-selected '+context['kind'],'selected_path':str(path)}} for p in files]
    import_library(db,{'version':1,'sources':sources},path.parent)
    return [s['id'] for s in sources]


def add_recording_arguments(parser):
    parser.add_argument('--recorded-date',required=True,help='Approximate YYYY, YYYY-MM or exact YYYY-MM-DD')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--seasonal',action='store_true')
    group.add_argument('--not-seasonal',dest='seasonal',action='store_false')
    parser.add_argument('--holiday',choices=HOLIDAYS)
    parser.add_argument('--holiday-year',type=int)


def arguments_context(args):
    return validate_context({'kind':'recorded','recorded_date':args.recorded_date,
        'seasonal':args.seasonal,'holiday':args.holiday,'holiday_year':args.holiday_year})
