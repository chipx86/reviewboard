from reviewboard.signals import initializing


def connect_signals(**kwargs):
    """
    Listens to the ``initializing`` signal and tells other modules to
    connect their signals. This is done so as to guarantee that django
    is loaded first.
    """
    from reviewboard.notifications import email
    from reviewboard.notifications import event_manager

    for module in [email, event_manager]:
        module.connect_signals()


initializing.connect(connect_signals)
