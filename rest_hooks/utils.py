def get_module(path):
    """
    A modified duplicate from Django's built in backend
    retriever.

        slugify = get_module('django.template.defaultfilters.slugify')
    """
    from django.utils.importlib import import_module

    try:
        mod_name, func_name = path.rsplit('.', 1)
        mod = import_module(mod_name)
    except ImportError, e:
        raise ImportError(
            'Error importing alert function {0}: "{1}"'.format(mod_name, e))

    try:
        func = getattr(mod, func_name)
    except AttributeError:
        raise ImportError(
            ('Module "{0}" does not define a "{1}" function'
                            ).format(mod_name, func_name))

    return func

def find_and_fire_hook(event_name, instance, user_override=None):
    """
    Look up Hooks that apply
    """
    from django.contrib.auth.models import User
    from rest_hooks.models import Hook, HOOK_EVENTS

    # specified user(s) to notify
    if user_override:
        users = user_override if isinstance(user_override, list) else [user_override]

    # has relationship with user table
    elif hasattr(instance, 'user'):
        users = [instance.user]

    # exposed property to tell us which users should be notified
    elif hasattr(instance, 'hook_users'):
        users = instance.hook_users

    # is a user object itself
    elif isinstance(instance, User):
        users = [instance]

    else:
        raise Exception(
            '{} has no `user` or `hook_users` property. REST Hooks needs this.'.format(repr(instance))
        )

    if not event_name in HOOK_EVENTS.keys():
        raise Exception(
            '"{}" does not exist in `settings.HOOK_EVENTS`.'.format(event_name)
        )

    hooks = Hook.objects.filter(user__in=users, event=event_name)
    for hook in hooks:
        hook.deliver_hook(instance)

def distill_model_event(instance, model, action, user_override=None):
    """
    Take created, updated and deleted actions for built-in 
    app/model mappings, convert to the defined event.name
    and let hooks fly.

    If that model isn't represented, we just quit silenty.
    """
    from rest_hooks.models import HOOK_EVENTS

    event_name = None
    for maybe_event_name, auto in HOOK_EVENTS.items():
        if auto:
            # break auto into App.Model, Action
            maybe_model, maybe_action = auto.rsplit('.', 1)
            if model == maybe_model and action == maybe_action:
                event_name = maybe_event_name

    if event_name:
        find_and_fire_hook(event_name, instance, user_override=user_override)
