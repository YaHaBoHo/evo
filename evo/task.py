

class Task():

    # timer [int] : Time before executing action.
    # action [function] : Callback, executed when timer expires.
    # update [function] : Callback, executed every tick, if it retruns [False] task will be aborted.

    VERB = "is busy"

    def __init__(self, timer, action=None, update=None):
        # Config
        self.timer = timer
        self._action = action
        self._update = update
        # Internals
        self.aborted = False

    def __bool__(self):
        return self.running 

    @property
    def running(self):
        return (self.timer > 0) and (not self.aborted)

    def action(self):
        if self._action and not self.aborted:
            self._action()

    def update(self):
        if self._update and not self.aborted:
            return self._update()
        # Otherwise just return True.
        return True

    def tick(self):
        # Only take action if not aborted
        if not self.aborted:
            # Validate ...
            if self.update() is False:
                self.aborted = True
            # ... and tick/execute.
            else:
                # Uodate
                self.timer -= 1
                self.update()
                # Execute action if done
                if self.timer <= 0:
                    self.action()


class Wean(Task):
    VERB = "weaning"


class Consume(Task):
    VERB = "consuming"


class Drink(Task):
    VERB = "drinking"


class Gestate(Task):
    VERB = "gestating" 
