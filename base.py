from threading import Thread
from kivymd.app import MDApp
from os import listdir
from os.path import join
from kivy.uix.image import Image
from kivy.storage.jsonstore import JsonStore
from kivymd.uix.chip import MDChip
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRectangleFlatIconButton
from kivymd.uix.list import IRightBodyTouch, OneLineRightIconListItem
from kivy.clock import mainthread, Clock
from kivymd.uix.widget import MDWidget
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel


class SettingsChip(MDChip):
    def on_long_touch(self, *args) -> None:
        pass


class BaseBtn(MDRectangleFlatIconButton):
    pass


class NoRippleBaseBtn(BaseBtn):
    def start_ripple(self) -> None:
        pass

    def finish_ripple(self) -> None:
        pass


class MultiChip(MDChip):
    def on_long_touch(self, *args) -> None:
        pass


class BaseLabel(MDLabel):
    pass


class GIF(Image):
    def __init__(self, **kwargs):
        src_dir = kwargs.pop("source")
        self.src = sorted([join(src_dir, f) for f in listdir(src_dir)], key=lambda x: int("".join([y for y in x if y.isnumeric()])))
        self.current = 0
        self.delay = 1
        self.original_delay = 1
        self.current_schedule = None
        self.modified = False
        self.finished_callback = None
        self.total_modified = 0
        kwargs.update({"source": self.src[self.current]})
        super().__init__(**kwargs)

    @property
    def remaining_frames(self) -> int:
        return len(self.source)-self.current-1

    @property
    def is_animating(self) -> bool:
        return self.current_schedule is not None

    @mainthread
    def next_frame(self) -> None:
        if self.remaining_frames:
            self.current += 1
            self.source = self.src[self.current]

    def reset(self) -> None:
        if self.is_animating:
            self.stop()
        self.current = 0
        self.total_modified = 0
        self.source = self.src[0]

    def stop(self, keep_schedule_ref: bool = False) -> None:
        self.current_schedule.cancel()
        self.total_modified = 0
        if not keep_schedule_ref:
            self.current_schedule = None

    def modify_delay(self, original_factor: float, tolerance_cap: int = 0, max_delay_increase_factor: float = None) -> None:
        if self.is_animating and (not tolerance_cap or tolerance_cap >= self.total_modified) and \
                (max_delay_increase_factor is None or (self.delay / max_delay_increase_factor) < self.original_delay):
            if not self.modified:
                self.original_delay = self.delay
                self.modified = True
            self.total_modified += 1
            self.delay += self.original_delay * (original_factor-1)

    def reset_delay(self, *_) -> None:
        self.delay = self.original_delay
        self.modified = False

    def start_animation_schedule(self, delay=None, repeat: bool = False, target_screen: list = None, instant: bool = False) -> None:
        if delay is not None:
            self.delay = delay
            self.original_delay = delay
        if not instant:
            self.current_schedule = Clock.schedule_once(lambda *_: self.__animate(repeat=repeat, target_screen=target_screen), self.delay)
        else:
            self.current_schedule = Clock.schedule_once(lambda *_: self.__animate(repeat=repeat, target_screen=target_screen))

    def __animate(self, repeat: bool = False, target_screen: list = None) -> None:
        delay = self.delay
        self.reset_delay()
        if target_screen is not None and target_screen[0].current != target_screen[1]:
            self.current_schedule = Clock.schedule_once(lambda *_: self.__animate(repeat=repeat, target_screen=target_screen), 0.2)
            return
        self.next_frame()
        if repeat or self.remaining_frames:
            self.current_schedule = Clock.schedule_once(
                lambda *_: self.__animate(repeat=repeat, target_screen=target_screen), delay)
        else:
            if self.finished_callback is not None:
                self.finished_callback()
            self.current_schedule = None


class ListItem(OneLineRightIconListItem):
    def __init__(self, *args, **kwargs):
        if "text" in kwargs.keys():
            self.txt = kwargs.pop("text")
        super().__init__(*args, **kwargs)

    def on_touch_down(self, touch) -> None:
        selected = [child for child in self.ids.container.children if child.collide_point(*touch.pos)]
        if selected:
            selected[0].on_touch_down(touch)


class ListItemHeader(OneLineRightIconListItem):
    def on_touch_down(self, touch) -> None:
        return


class ListItemContainer(IRightBodyTouch, MDBoxLayout):
    adaptive_width = True


class ItemSeparator(MDWidget):
    """Separator Widget"""


class BaseTextField(MDTextField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_text_func = None

    def set_text(self, instance_text_field, text: str) -> None:
        super().set_text(instance_text_field, text)
        if self.set_text_func is not None and text:
            self.set_text_func()


class BaseApp(MDApp):
    """
    Provides some basic JsonStore functionality to store data and options/settings for the app and uses a
    Dark / BlueGray theme \n
    Also has a method to toggle a SettingsChip (see SettingsChip class) \n
    This is a base class and hence should be inherited from and not be instantiated on its own
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.store_name = "data.json"
        self.options = {}
        self.data = {}

    def build(self) -> None:
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.theme_text_color = (1, 1, 1, 1)

    def on_start(self) -> None:
        self.store = JsonStore(self.store_name)
        del self.store_name
        self.check_store()
        if hasattr(self, "on_startup"):
            Thread(target=self.on_startup).start()

    def on_stop(self):
        self.save_store()

    def on_pause(self):
        self.save_store()
        return True

    def save_store(self) -> None:
        self.store.put("options", **self.options)
        self.store.put("data", **self.data)

    def check_store(self, options_defaults_to: dict = None, data_defaults_to: dict = None) -> None:
        try:
            options = self.store.get("options")
            if options_defaults_to is not None:
                options.update({k: v for k, v in options.items() if v is None and k in options_defaults_to.keys()})
            self.store.put("options", **options)
        except KeyError:
            if options_defaults_to is not None:
                self.store.put("options", **options_defaults_to)
                options = options_defaults_to
            else:
                options = {}
        try:
            data = self.store.get("data")
            if data_defaults_to is not None:
                data.update({k: v for k, v in data.items() if v is None and k in data_defaults_to.keys()})
        except KeyError:
            if data_defaults_to is not None:
                self.store.put("data", **data_defaults_to)
                data = data_defaults_to
            else:
                data = {}
        self.data = data
        self.options = options

    def toggle_chip(self, obj) -> None:
        obj.toggled = not obj.toggled

    def increase_counter(self, root) -> None:
        nval = int(root.ids.current_count.text) + 1
        if nval > 0:
            root.ids.current_count.text = str(nval)

    def decrease_counter(self, root) -> None:
        nval = int(root.ids.current_count.text)-1
        if nval > 0:
            root.ids.current_count.text = str(nval)

    @mainthread
    def set_counter(self, root, value: str) -> None:
        root.ids.current_count.text = value

    @staticmethod
    def toggle_multi_chip(selected):
        selected.toggled = True
        for chip in selected.parent.children:
            if isinstance(chip, MultiChip) and chip != selected:
                chip.toggled = False
