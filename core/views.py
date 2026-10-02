import calendar
from datetime import date, datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.http import HttpResponse, JsonResponse
from django.templatetags.static import static

from .models import (
    MEAL_FIELDS, CalorieEntry, Cheer, Friendship, MealLog, Profile, WeightEntry,
)
from django.http import JsonResponse
MEAL_LABELS = {
    'breakfast': 'Breakfast',
    'lunch': 'Lunch',
    'snacks': 'Evening snacks',
    'dinner': 'Dinner',
}

MEAL_HINTS = {
    'breakfast': 'Morning',
    'lunch': 'Midday',
    'snacks': 'Evening',
    'dinner': 'Night',
}

def _is_ajax(request):
    return request.headers.get('X-Requested-With') == 'fetch'


def _motivation(weekly, streak):
    if weekly['progress'] >= 100:
        return 'Target hit. Great week!'
    if weekly['progress'] > 50:
        return 'More than halfway. Keep going.'
    if streak > 2:
        return f'{streak} days in a row. Nice rhythm.'
    return 'Small steps count. Show up today.'
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def profile_required(view):
    """Login required AND onboarding finished (user has a Profile)."""
    def wrapper(request, *args, **kwargs):
        if not hasattr(request.user, 'profile'):
            return redirect('onboarding')
        return view(request, *args, **kwargs)
    return login_required(wraps(view)(wrapper))


def _num(value, low=20, high=300):
    """Parse a weight-like number. Returns a float rounded to 1 decimal, or None."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return round(n, 1) if low <= n <= high else None


def _name(user):
    return user.first_name or 'Member'


# ---------------------------------------------------------------------------
# Public pages and authentication
# ---------------------------------------------------------------------------
def landing_view(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile'):
        return redirect('home')
    return render(request, 'landing.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    context = {}
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        error = None

        if not (name and email and password):
            error = 'Fill in all fields.'
        elif '@' not in email:
            error = 'Enter a valid email address.'
        elif User.objects.filter(username=email).exists():
            error = 'An account with this email already exists. Try logging in.'
        else:
            try:
                validate_password(password, User(username=email, email=email, first_name=name))
            except ValidationError as e:
                error = ' '.join(e.messages)

        if error:
            messages.error(request, error)
            context = {'form_name': name, 'form_email': email}
        else:
            user = User.objects.create_user(
                username=email, email=email, password=password, first_name=name,
            )
            login(request, user)
            return redirect('onboarding')

    return render(request, 'signup.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    context = {}
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, 'Email or password is incorrect.')
            context = {'form_email': email}
        else:
            login(request, user)
            if hasattr(user, 'profile'):
                return redirect('home')
            return redirect('onboarding')

    return render(request, 'login.html', context)


@require_POST
def logout_view(request):
    logout(request)
    return redirect('landing')


@login_required
def onboarding_view(request):
    if hasattr(request.user, 'profile'):
        return redirect('home')

    context = {'goal': 'gain'}
    if request.method == 'POST':
        goal = request.POST.get('goal', 'gain')
        current = _num(request.POST.get('current_weight'))
        desired = _num(request.POST.get('desired_weight'))
        error = None

        if goal not in ('gain', 'lose'):
            error = 'Pick a goal.'
        elif current is None or desired is None:
            error = 'Enter both weights in kg (between 20 and 300).'
        elif goal == 'gain' and desired <= current:
            error = 'For gaining weight, your desired weight should be higher than your current weight.'
        elif goal == 'lose' and desired >= current:
            error = 'For losing weight, your desired weight should be lower than your current weight.'

        if error:
            messages.error(request, error)
            context = {
                'goal': goal,
                'form_current': request.POST.get('current_weight', ''),
                'form_desired': request.POST.get('desired_weight', ''),
            }
        else:
            Profile.objects.create(
                user=request.user, goal=goal, start_weight=current, target_weight=desired,
            )
            messages.success(request, 'You are all set. Let\'s start tracking!')
            return redirect('home')

    return render(request, 'onboarding.html', context)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
@profile_required
def home_view(request):
    me = request.user
    profile = me.profile
    today = timezone.localdate()

    log = MealLog.objects.filter(user=me, date=today).first()
    meals = [
        {
            'key': f,
            'label': MEAL_LABELS[f],
            'hint': MEAL_HINTS[f],
            'value': getattr(log, f) if log else None,
        }
        for f in MEAL_FIELDS
    ]
    weight_today = WeightEntry.objects.filter(user=me, date=today).first()
    weekly = profile.weekly_target()
    streak = profile.streak()
    motivation = _motivation(weekly, streak)

    if weekly['progress'] >= 100:
        motivation = 'Target hit. Great week!'
    elif weekly['progress'] > 50:
        motivation = 'More than halfway. Keep going.'
    elif streak > 2:
        motivation = f'{streak} days in a row. Nice rhythm.'
    else:
        motivation = 'Small steps count. Show up today.'

    hour = timezone.localtime().hour
    greeting = 'Good morning' if hour < 12 else 'Good afternoon' if hour < 18 else 'Good evening'

    current = weekly['current']
    since_start = round(current - profile.start_weight, 1)
    to_go = round(abs(profile.target_weight - current), 1)

    return render(request, 'home.html', {
        'active': 'home',
        'profile': profile,
        'greeting': greeting,
        'weekly': weekly,
        'streak': streak,
        'motivation': motivation,
        'meals': meals,
        'yes_count': log.yes_count if log else 0,
        'weight_today': weight_today,
        'last_weight': profile.latest_weight(),
        'since_start': since_start,
        'to_go': to_go,
    })
@profile_required
@require_POST
def save_meal(request):
    meal = request.POST.get('meal')
    answer = request.POST.get('answer')
    valid = meal in MEAL_FIELDS and answer in ('yes', 'no')

    log = None
    if valid:
        log, _ = MealLog.objects.get_or_create(user=request.user, date=timezone.localdate())
        setattr(log, meal, answer == 'yes')
        log.save()

    if _is_ajax(request):
        if not valid:
            return JsonResponse({'ok': False}, status=400)
        return JsonResponse({
            'ok': True,
            'yes_count': log.yes_count,
            'streak': request.user.profile.streak(),
        })
    return redirect('home')


@profile_required
@require_POST
def save_weight(request):
    weight = _num(request.POST.get('weight'))
    if weight is None:
        if _is_ajax(request):
            return JsonResponse({'ok': False, 'message': 'Enter a valid weight in kg.'}, status=400)
        messages.error(request, 'Enter a valid weight in kg.')
        return redirect('home')

    WeightEntry.objects.update_or_create(
        user=request.user, date=timezone.localdate(), defaults={'weight': weight},
    )

    if _is_ajax(request):
        profile = request.user.profile
        weekly = profile.weekly_target()
        streak = profile.streak()
        return JsonResponse({
            'ok': True,
            'message': 'Weight saved.',
            'progress': weekly['progress'],
            'target': weekly['target'],
            'current': weekly['current'],
            'since_start': round(weekly['current'] - profile.start_weight, 1),
            'to_go': round(abs(profile.target_weight - weekly['current']), 1),
            'streak': streak,
            'motivation': _motivation(weekly, streak),
        })

    messages.success(request, 'Weight saved.')
    return redirect('home')


@profile_required
@require_POST
def cheer_friend(request, user_id):
    other = get_object_or_404(User, id=user_id)
    friendship = Friendship.between(request.user, other)
    is_friend = friendship is not None and friendship.status == 'accepted'

    if is_friend:
        _, created = Cheer.objects.get_or_create(
            from_user=request.user, to_user=other, date=timezone.localdate(),
        )
        if _is_ajax(request):
            return JsonResponse({'ok': True, 'message': f'You cheered {_name(other)}.'})
        if created:
            messages.success(request, f'You cheered {_name(other)}.')
    elif _is_ajax(request):
        return JsonResponse({'ok': False}, status=400)
    return redirect('friends')


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
@profile_required
def stats_view(request):
    me = request.user
    today = timezone.localdate()

    # Month to show (?m=2026-10). Defaults to the current month.
    try:
        year, month = [int(x) for x in request.GET.get('m', '').split('-')]
        first_of_month = date(year, month, 1)
    except (ValueError, TypeError):
        first_of_month = today.replace(day=1)
    if first_of_month > today.replace(day=1):
        first_of_month = today.replace(day=1)
    year, month = first_of_month.year, first_of_month.month

    prev_month = (first_of_month - timedelta(days=1)).replace(day=1)
    next_month = (first_of_month + timedelta(days=32)).replace(day=1)
    has_next = next_month <= today.replace(day=1)

    # Calendar cells
    weeks_dates = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    start, end = weeks_dates[0][0], weeks_dates[-1][-1]
    weights = {w.date: w.weight for w in WeightEntry.objects.filter(user=me, date__range=(start, end))}
    logs = {m.date: m for m in MealLog.objects.filter(user=me, date__range=(start, end))}

    weeks = []
    for week in weeks_dates:
        row = []
        for d in week:
            yes = logs[d].yes_count if d in logs else 0
            row.append({
                'date': d,
                'in_month': d.month == month,
                'is_today': d == today,
                'weight': weights.get(d),
                'yes': yes,
                'dots': [i < yes for i in range(4)],
            })
        weeks.append(row)

    # Chart data: last 21 days (weights fetched 6 days earlier for the 7-day average)
    days = [today - timedelta(days=i) for i in range(20, -1, -1)]
    w_map = {w.date: w.weight for w in WeightEntry.objects.filter(
        user=me, date__range=(days[0] - timedelta(days=6), today))}
    c_map = {r['date']: r['total'] for r in CalorieEntry.objects.filter(
        user=me, date__range=(days[0], today)).values('date').annotate(total=Sum('kcal'))}
    m_map = {m.date: m.yes_count for m in MealLog.objects.filter(user=me, date__range=(days[0], today))}

    avg = []
    for d in days:
        window = [w_map[d - timedelta(days=i)] for i in range(7) if (d - timedelta(days=i)) in w_map]
        avg.append(round(sum(window) / len(window), 2) if window else None)

    chart_data = {
        'labels': [d.strftime('%d %b') for d in days],
        'weight': [w_map.get(d) for d in days],
        'avg': avg,
        'calories': [c_map.get(d) for d in days],
        'meals': [m_map.get(d) for d in days],
    }

    return render(request, 'stats.html', {
        'active': 'stats',
        'profile': me.profile,
        'weeks': weeks,
        'month_label': first_of_month.strftime('%B %Y'),
        'prev_month': prev_month.strftime('%Y-%m'),
        'next_month': next_month.strftime('%Y-%m'),
        'has_next': has_next,
        'chart_data': chart_data,
    })


# ---------------------------------------------------------------------------
# Friends and leaderboard
# ---------------------------------------------------------------------------
@profile_required
def friends_view(request):
    me = request.user
    today = timezone.localdate()
    tab = request.GET.get('tab', 'friends')
    if tab not in ('friends', 'compete'):
        tab = 'friends'
    q = request.GET.get('q', '').strip()

    friend_users = list(Friendship.friends_of(me).filter(profile__isnull=False).select_related('profile'))

    logs = {m.user_id: m for m in MealLog.objects.filter(user__in=friend_users, date=today)}
    cheered = set(Cheer.objects.filter(from_user=me, date=today).values_list('to_user_id', flat=True))

    friend_rows = []
    for u in friend_users:
        log = logs.get(u.id)
        dots = [getattr(log, f) is True for f in MEAL_FIELDS] if log else [False] * 4
        friend_rows.append({
            'user': u,
            'name': _name(u),
            'initial': _name(u)[0].upper(),
            'streak': u.profile.streak(),
            'dots': dots,
            'done': sum(dots),
            'cheered': u.id in cheered,
        })

    # Requests waiting for me
    incoming = Friendship.objects.filter(to_user=me, status='pending').select_related('from_user')

    # Search (by name, or exact email)
    results = []
    if q:
        relations = {}
        for f in Friendship.objects.filter(Q(from_user=me) | Q(to_user=me)):
            other = f.to_user_id if f.from_user_id == me.id else f.from_user_id
            relations[other] = f
        found = (User.objects.filter(profile__isnull=False).exclude(id=me.id)
                 .filter(Q(first_name__icontains=q) | Q(username__iexact=q))[:10])
        for u in found:
            f = relations.get(u.id)
            if f is None:
                state = 'none'
            elif f.status == 'accepted':
                state = 'friends'
            elif f.from_user_id == me.id:
                state = 'requested'
            else:
                state = 'incoming'
            results.append({
                'user': u, 'name': _name(u), 'initial': _name(u)[0].upper(), 'state': state,
            })

    # Leaderboard: meals answered "yes" in the last 7 days (max 28)
    week_start = today - timedelta(days=6)
    board_users = [me] + [u for u in friend_users]
    totals = {u.id: 0 for u in board_users}
    for m in MealLog.objects.filter(user__in=board_users, date__range=(week_start, today)):
        totals[m.user_id] += m.yes_count
    board = sorted(
        [{
            'user': u,
            'name': 'You' if u.id == me.id else _name(u),
            'initial': _name(u)[0].upper(),
            'score': totals[u.id],
            'is_me': u.id == me.id,
        } for u in board_users],
        key=lambda r: r['score'], reverse=True,
    )
    for i, row in enumerate(board, start=1):
        row['rank'] = i

    return render(request, 'friends.html', {
        'active': 'friends',
        'profile': me.profile,
        'tab': tab,
        'q': q,
        'friends': friend_rows,
        'incoming': incoming,
        'results': results,
        'board': board,
    })


@profile_required
@require_POST
def send_request(request, user_id):
    me = request.user
    target = get_object_or_404(User, id=user_id, profile__isnull=False)
    if target == me:
        return redirect('friends')

    existing = Friendship.between(me, target)
    if existing is None:
        Friendship.objects.create(from_user=me, to_user=target)
        messages.success(request, f'Request sent to {_name(target)}.')
    elif existing.status == 'pending' and existing.from_user_id == target.id:
        # They already asked us, so sending one back accepts it.
        existing.status = 'accepted'
        existing.save()
        messages.success(request, f'You and {_name(target)} are now friends.')
    else:
        messages.info(request, 'You are already connected or a request is pending.')
    return redirect('friends')


@profile_required
@require_POST
def respond_request(request, pk, action):
    friendship = get_object_or_404(Friendship, pk=pk, to_user=request.user, status='pending')
    if action == 'accept':
        friendship.status = 'accepted'
        friendship.save()
        messages.success(request, f'You and {_name(friendship.from_user)} are now friends.')
    elif action == 'decline':
        friendship.delete()
        messages.info(request, 'Request declined.')
    return redirect('friends')


@profile_required
@require_POST
def remove_friend(request, user_id):
    other = get_object_or_404(User, id=user_id)
    friendship = Friendship.between(request.user, other)
    if friendship and friendship.status == 'accepted':
        friendship.delete()
        messages.info(request, f'{_name(other)} removed from your group.')
    return redirect('friends')



# ---------------------------------------------------------------------------
# Calories (fully independent tracker)
# ---------------------------------------------------------------------------
@profile_required
def calories_view(request):
    me = request.user
    today = timezone.localdate()

    entries = CalorieEntry.objects.filter(user=me, date=today)
    total_today = entries.aggregate(total=Sum('kcal'))['total'] or 0
    history = (CalorieEntry.objects.filter(user=me).values('date')
               .annotate(total=Sum('kcal')).order_by('-date')[:7])

    return render(request, 'calories.html', {
        'active': 'calories',
        'profile': me.profile,
        'entries': entries,
        'total_today': total_today,
        'history': history,
    })


@profile_required
@require_POST
def add_calorie(request):
    name = request.POST.get('name', '').strip()[:100]
    try:
        kcal = int(request.POST.get('kcal', ''))
    except ValueError:
        kcal = 0
    if not name or not (0 < kcal <= 10000):
        messages.error(request, 'Add what you ate and a calorie number.')
    else:
        CalorieEntry.objects.create(user=request.user, date=timezone.localdate(), name=name, kcal=kcal)
    return redirect('calories')


@profile_required
@require_POST
def delete_calorie(request, pk):
    get_object_or_404(CalorieEntry, pk=pk, user=request.user).delete()
    return redirect('calories')


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------
@profile_required
def profile_view(request):
    profile = request.user.profile

    if request.method == 'POST':
        goal = request.POST.get('goal', profile.goal)
        target = _num(request.POST.get('target_weight'))
        reminder = request.POST.get('reminder_time', '')
        error = None

        if goal not in ('gain', 'lose'):
            error = 'Pick a valid goal.'
        elif target is None:
            error = 'Enter a valid desired weight in kg.'
        else:
            try:
                reminder_time = datetime.strptime(reminder, '%H:%M').time()
            except ValueError:
                error = 'Enter a valid reminder time.'

        if error:
            messages.error(request, error)
        else:
            profile.goal = goal
            profile.target_weight = target
            profile.reminder_time = reminder_time
            profile.save()
            messages.success(request, 'Profile updated.')
        return redirect('profile')

    return render(request, 'profile.html', {
        'active': 'profile',
        'profile': profile,
        'reminder_value': profile.reminder_time.strftime('%H:%M'),
    })

# ---------------------------------------------------------------------------
# Install as app (PWA)
# ---------------------------------------------------------------------------
def manifest_view(request):
    data = {
        'id': '/',
        'name': 'WeightPalz',
        'short_name': 'WeightPalz',
        'description': 'Four taps a day. Build the habit of gaining or losing weight.',
        'start_url': '/home/',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'background_color': '#0c0f13',
        'theme_color': '#0c0f13',
        'categories': ['health', 'fitness', 'lifestyle'],
        'icons': [
            {'src': static('icons/icon-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('icons/icon-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('icons/icon-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
    }
    return JsonResponse(data, content_type='application/manifest+json')


SERVICE_WORKER_JS = """
const CACHE = 'weightpalz-v1';
const OFFLINE_HTML = '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>Offline</title><body style="margin:0;min-height:100vh;display:grid;place-content:center;gap:12px;text-align:center;' +
  'background:#0c0f13;color:#f4f7fa;font-family:system-ui,sans-serif;padding:24px">' +
  '<h2>You are offline</h2><p style="color:#8b96a5">Connect to the internet to log your check-in.</p>' +
  '<button onclick="location.reload()" style="background:#35f0b4;color:#05140e;border:0;border-radius:99px;padding:13px 22px;font-weight:600">Try again</button>';

self.addEventListener('install', function () { self.skipWaiting(); });

self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys()
      .then(function (keys) {
        return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
      })
      .then(function () { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  var url = new URL(req.url);
  if (url.origin !== location.origin) return;

  // Static files: network first, cached copy if the network is down
  if (url.pathname.indexOf('/static/') === 0) {
    e.respondWith(
      fetch(req).then(function (res) {
        if (res.ok) { var copy = res.clone(); caches.open(CACHE).then(function (c) { c.put(req, copy); }); }
        return res;
      }).catch(function () { return caches.match(req); })
    );
    return;
  }

  // Pages: always from the server, friendly message if offline
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req).catch(function () {
        return new Response(OFFLINE_HTML, { headers: { 'Content-Type': 'text/html; charset=utf-8' } });
      })
    );
  }
});
"""


def service_worker_view(request):
    # Served from the site root so it can control every page.
    response = HttpResponse(SERVICE_WORKER_JS, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache'
    return response