import json
from kivy.clock import mainthread
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog

from Scraper import VerbenScraper
from base import BaseApp, ListItem, ItemSeparator, GIF, BaseLabel


class Scraper(VerbenScraper):
    def __init__(self, multi_update_callback=None):
        super().__init__()
        self.multi_update_callback = multi_update_callback

    @staticmethod
    def load_data(only_data: bool = True) -> dict:
        try:
            with open("./data.json", "r") as data_file:
                try:
                    data = json.load(data_file)
                except Exception:
                    data = {}
            if only_data:
                return data.get("data", {})
            else:
                return data
        except FileNotFoundError:
            return {}

    def save_data(self) -> None:
        settings = self.load_data(only_data=False)
        if "data" in settings:
            del settings["data"]
        with open("./data.json", "w") as file:
            json.dump({"data": self.data, **settings}, file)

    def multi_update_on_finish_callback(self, saving: bool):
        super().multi_update_on_finish_callback(saving)
        if self.multi_update_callback is not None:
            self.multi_update_callback()


class LateinVerbenApp(BaseApp):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.Scraper = Scraper(multi_update_callback=self.get_data_callback)
        self.current_words_widgets = []
        self.current_words_separators = []
        self.remove_dialog = None
        self.current_question = None
        self.nothing_found_label = BaseLabel(text="Es konnten keine Vokabel Daten gefunden werden."
                                                "\nBitte aktualisieren sie die Vokabel Daten.", text_color=(1, 1, 1, 1),
                                           halign="center", font_style="H4", theme_text_color="Custom")
        self.GIF = GIF(source="./frames/")
        self.stopped = False

    def on_start(self) -> None:
        super().on_start()
        self.GIF.finished_callback = self.time_is_up
        self.success_label = self.root.ids.success_label
        self.failure_label = self.root.ids.failure_label

    def on_startup(self):
        self.load_from_scraper()
        self.start_quiz()
        self.load_gif()
        self.GIF.bind(size=self.adjust_block_size)

    def save_store(self) -> None:
        self.options.update({"counters": {"correct": self.root.ids.correct_counter.text, "incorrect":
            self.root.ids.incorrect_counter.text}})
        super().save_store()

    def check_store(self, options_defaults_to: dict = None, data_defaults_to: dict = None) -> None:
        super().check_store(options_defaults_to, data_defaults_to)
        self.set_correct_incorrect_counters()
        toggle_settings = self.options.get("toggle_settings", {})
        self.root.ids.delete_confirmation.toggled = toggle_settings.get("delete_confirmation", True)
        getattr(self.root.ids, {1.2: "easy", 0.65: "moderat", 0.4: "hard", 2: "very_easy"}.get(self.options.get("delay", 1.2), "easy")).toggled = True
        self.root.ids.ignore_gender_parti.toggled = toggle_settings.get("ignore_gender_parti", True)
        self.root.ids.ignore_gender_geru.toggled = toggle_settings.get("ignore_gender_geru", False)
        self.root.ids.exclude_imp2.toggled = toggle_settings.get("exclude_imp2", True)
        self.root.ids.exclude_supina.toggled = toggle_settings.get("exclude_supina", True)

    def adjust_block_size(self, *_):
        x, y = self.GIF.get_norm_image_size()
        self.root.ids.block_container.size = (x/3, y/3)
        self.root.ids.block_container.x = self.GIF.get_center_x()-x/2.5
        self.root.ids.block_container.y = self.GIF.get_center_y()-y/2.75

    @mainthread
    def set_correct_incorrect_counters(self):
        self.root.ids.correct_counter.text = self.options.get("counters", {}).get("correct", "Richtig: 0")
        self.root.ids.incorrect_counter.text = self.options.get("counters", {}).get("incorrect", "Falsch: 0")

    def reset_correct_incorrect_counters(self):
        if "counters" in self.options.keys():
            self.options.get("counters", {}).update({"correct": "Richtig: 0", "incorrect": "Falsch: 0"})
        else:
            self.options.update({"counters": {"correct": "Richtig: 0", "incorrect": "Falsch: 0"}})
        self.set_correct_incorrect_counters()

    @mainthread
    def load_gif(self):
        self.root.ids.main_box.add_widget(self.GIF)
        self.root.ids.main_box.add_widget(ItemSeparator())

    @mainthread
    def add_list_item(self, text: str):
        Sep = ItemSeparator()
        Item = ListItem(text=text)
        Item.children[1].children[0].children[0].toggled = self.options.get("toggled", {}).get(text, True)
        self.current_words_separators.append(Sep)
        self.current_words_widgets.append(Item)
        self.root.ids.current_words_box.add_widget(Sep)
        self.root.ids.current_words_box.add_widget(Item)

    @mainthread
    def add_nothing_found_label(self):
        self.current_words_separators.extend([ItemSeparator(height=self.root.ids.list_header.height), ItemSeparator(), ItemSeparator(), ItemSeparator()])
        for sep in self.current_words_separators:
            self.root.ids.current_words_box.add_widget(sep)
        self.root.ids.current_words_box.add_widget(self.nothing_found_label)

    @mainthread
    def remove_nothing_found_label(self):
        for sep in self.current_words_separators:
            self.root.ids.current_words_box.remove_widget(sep)
        self.root.ids.current_words_box.remove_widget(self.nothing_found_label)

    def submit_answer(self, instance, *_):
        if instance.text and self.current_question is not None and "Zeit ist um!" not in self.root.ids.timed_out_label.text:
            if isinstance(self.current_question[1], str):
                if instance.text.lower().strip() == self.current_question[1].lower().strip():
                    self.stop_gif()
                    self.increase_correct_score()
                    self.display_correct_answer()
                    self.correct_text_field(self.root.ids.validate_field)
                else:
                    self.incorrect_text_field(self.root.ids.validate_field)
            else:
                if instance.text.lower().strip() in [t.lower().strip() for t in self.current_question[1]]:
                    self.stop_gif()
                    self.increase_correct_score()
                    self.display_correct_answer()
                    self.correct_text_field(self.root.ids.validate_field)
                else:
                    self.incorrect_text_field(self.root.ids.validate_field)

    def display_correct_answer(self):
        self.root.ids.timed_out_label.text = f"[color=#9999cc]{self.current_question[0].replace('Was ist ', '').replace('?', '')} ist [size=35]{self.current_question[1]}[/size][/color]"

    def toggle_text_field(self, text_field):
        if text_field.line_color_focus == (0, 1, 0, 1):
            self.incorrect_text_field(text_field)
        else:
            self.correct_text_field(text_field)

    @staticmethod
    def correct_text_field(text_field):
        text_field.error = True
        text_field.color_mode = "Custom"
        text_field.helper_text = "Richtig!"
        text_field.error_color = (0, 1, 0, 1)
        text_field.set_active_underline_color((0, 1, 0, 1))
        text_field.set_helper_text_color((0, 1, 0, 1))
        text_field.icon_left_color_normal = (0, 1, 0, 1)
        text_field.icon_left_color_focused = (0, 1, 0, 1)

    @staticmethod
    def reset_text_field(text_field):
        text_field.error = False
        text_field.color_mode = "accent"
        text_field.icon_left_color_normal = (0.2980392156862745, 0.5058823529411764, 0.6313725490196078, 1)
        text_field.icon_left_color_focused = (0.2980392156862745, 0.5058823529411764, 0.6313725490196078, 1)

    @staticmethod
    def incorrect_text_field(text_field, text: str = "Falsch!"):
        text_field.error = True
        text_field.color_mode = "Custom"
        text_field.helper_text = text
        text_field.error_color = (1, 0, 0, 1)
        text_field.set_active_underline_color((1, 0, 0, 1))
        text_field.set_helper_text_color((1, 0, 0, 1))
        text_field.icon_left_color_normal = (1, 0, 0, 1)
        text_field.icon_left_color_focused = (1, 0, 0, 1)

    def time_is_up(self, *_):
        self.incorrect_text_field(self.root.ids.validate_field, f"Die Zeit ist um!")
        self.root.ids.timed_out_label.text = f"[size=40]Die Zeit ist um![/size]\n[color=#9999cc]{self.current_question[0].replace('Was ist ', '').replace('?', '')}" \
                                             f"ist [size=35]{self.current_question[1]}[/size][/color]"
        self.increase_incorrect_score()

    @mainthread
    def increase_correct_score(self):
        self.root.ids.correct_counter.text = f"Richtig: {int(self.root.ids.correct_counter.text[self.root.ids.correct_counter.text.rfind(' ')+1:])+1}"

    @mainthread
    def increase_incorrect_score(self):
        self.root.ids.incorrect_counter.text = f"Falsch: {int(self.root.ids.incorrect_counter.text[self.root.ids.incorrect_counter.text.rfind(' ')+1:])+1}"

    def remove_time_is_up_label(self):
        self.root.ids.timed_out_label.text = ""

    def stop_gif(self):
        self.root.ids.validate_field.set_text_func = None
        self.GIF.stop(keep_schedule_ref=True)

    def animate_gif(self):
        self.GIF.start_animation_schedule(target_screen=[self.root.ids.nav.children[1], "screen 1"], delay=self.options.get("delay", 1.2))
        self.root.ids.validate_field.set_text_func = lambda *_: self.GIF.modify_delay(1.25, tolerance_cap=len(self.current_question[1]), max_delay_increase_factor=1.75)

    def start_quiz(self):
        if self.stopped:
            self.stopped = False
            self.root.ids.stop_btn.ripple_color = (1, 0, 0, 0.3)
            self.root.ids.stop_btn.md_bg_color = (0.686, 0.133, 0.133)
            self.root.ids.stop_btn.line_color = "orange"
            self.root.ids.stop_btn.icon_color = "orange"
            self.root.ids.stop_btn.text = "Stop"
        exclude = [t for t in self.Scraper.data.keys() if not self.options.get("toggled", {}).get(t, True)]
        self.root.ids.validate_field.text = ""
        self.GIF.reset()
        self.reset_text_field(self.root.ids.validate_field)
        if set(exclude) != set(self.Scraper.data.keys()):
            self.remove_time_is_up_label()
            if self.current_question is not None:
                self.display_correct_answer()
            self.current_question = self.Scraper.get_random_question(ignore_gender_parti=self.from_toggle_settings("ignore_gender_parti"),
                                                                     exclude_choice=exclude, ignore_gender_gerundivum=self.from_toggle_settings("ignore_gender_geru", defaults_to=False),
                                                                     exclude_imperativ_2=self.from_toggle_settings("exclude_imp2"), exclude_tense=["Supina"] if self.from_toggle_settings("exclude_supina") else [])
            self.reset_text_field(self.root.ids.validate_field)
            self.root.ids.current_q.text = self.current_question[0]
            self.animate_gif()
        else:
            self.root.ids.current_q.text = "Keine Daten vorhanden/ausgewählt"

    def from_toggle_settings(self, value, defaults_to=True):
        return self.options.get("toggle_settings", {}).get(value, defaults_to)

    def load_from_scraper(self):
        if self.Scraper.currently_contained:
            for word in self.Scraper.currently_contained:
                self.add_list_item(word)
        else:
            self.add_nothing_found_label()

    def open_remove_dialog(self, item: ListItem):
        self.last_pressed_item_delete = item
        if self.root.ids.delete_confirmation.toggled:
            if self.remove_dialog is None:
                self.remove_dialog = MDDialog(
                    text="Wollen sie diesen Eintrag mitsamt Daten wirklich löschen?",
                    buttons=[MDFlatButton(text="Abbrechen", theme_text_color="Custom",
                                          text_color=self.theme_cls.primary_color,
                                          on_release=lambda *_: self.remove_dialog.dismiss()),
                             MDFlatButton(text="Löschen", theme_text_color="Custom",
                                          text_color=(0.686, 0.133, 0.133, 1),
                                          on_release=self.dialog_delete)])
            self.remove_dialog.open()
        else:
            self.remove_item(self.last_pressed_item_delete)

    def dialog_delete(self, *_):
        self.remove_dialog.dismiss()
        self.remove_item(self.last_pressed_item_delete)

    def remove_item(self, item: ListItem):
        if item in self.current_words_widgets:
            i = self.current_words_widgets.index(item)
            self.root.ids.current_words_box.remove_widget(self.current_words_separators[i])
            self.root.ids.current_words_box.remove_widget(item)
            del self.current_words_widgets[i], self.current_words_separators[i]

            try:
                del self.data[item.children[0].text]
            except Exception:
                pass
            try:
                del self.Scraper.data[item.children[0].text]
            except Exception:
                pass
            try:
                del self.options["toggled"][item.children[0].text]
            except Exception:
                pass

            if not self.current_words_separators and not self.current_words_widgets:
                self.add_nothing_found_label()

    def toggle_chip(self, obj) -> None:
        super().toggle_chip(obj)
        if hasattr(obj, "toggling_options"):
            if "toggled" in self.options.keys():
                self.options.get("toggled").update({obj.parent.parent.parent.children[0].text: obj.toggled})
            else:
                self.options.update({"toggled": {obj.parent.parent.parent.children[0].text: obj.toggled}})
        elif obj.text == "Nach Löschbestätigung für Vokabeln fragen?":
            self.set_toggle_settings(obj.toggled, "delete_confirmation")
        elif obj.text == "Geschlecht bei Partizipien vernachlässigen?":
            self.set_toggle_settings(obj.toggled, "ignore_gender_parti")
        elif obj.text == "Geschlecht bei Gerundivum vernachlässigen?":
            self.set_toggle_settings(obj.toggled, "ignore_gender_geru")
        elif obj.text == "Imperativ II ausschließen?":
            self.set_toggle_settings(obj.toggled, "exclude_imp2")
        elif obj.text == "Supina ausschließen?":
            self.set_toggle_settings(obj.toggled, "exclude_supina")

    def set_toggle_settings(self, state, value):
        if "toggle_settings" in self.options.keys():
            self.options.get("toggle_settings").update({value: state})
        else:
            self.options.update({"toggle_settings": {value: state}})

    def update_current_words_list(self):
        for to_add in [t for t in self.Scraper.data.keys() if t not in [x.children[0].text for x in self.current_words_widgets]]:
            self.add_list_item(to_add)

    @mainthread
    def get_data_callback(self):
        self.data = self.Scraper.data

        if self.failure_label.text:
            self.failure_label.text = ""
        if self.success_label.text:
            self.success_label.text = ""

        if self.Scraper.failures:
            failure = ', '.join(list({x.replace('\n', '').strip() for x in self.Scraper.failures}))
            self.failure_label.text = f"Folgende Vokabeln wurden nicht gefunden: {failure}"
            self.Scraper.failures.clear()
            self.failure_label.text_color = (1, 0, 0, 1)
        if self.Scraper.success:
            success = ', '.join(list({x.replace('\n', '').strip() for x in self.Scraper.success}))
            self.success_label.text = f"Folgende Vokabeln wurden hinzugefügt: {success}"
            self.Scraper.success.clear()
            self.success_label.text_color = (0, 1, 0, 1)

        self.root.ids.get_data_field.text = ""

        if self.Scraper.currently_contained:
            self.remove_nothing_found_label()

        self.update_current_words_list()

    def validate_get_data(self, *_):
        self.root.ids.get_data_btn.disabled = True
        if self.root.ids.get_data_field.text:
            self.Scraper.assert_data_contains(list({y for x in self.root.ids.get_data_field.text.split(",") if (y := x.strip().lower())}), joining=False)
        self.root.ids.get_data_btn.disabled = False

    def toggle_multi_chip(self, selected):
        super().toggle_multi_chip(selected)
        if selected.text in ["Einfach", "Sehr Einfach", "Schwierig", "Moderat"]:
            self.options.update({"delay": {"Einfach": 1.2, "Sehr Einfach": 2, "Moderat": 0.65, "Schwierig": 0.4}.get(selected.text)})
            self.GIF.original_delay = self.options.get("delay", 1.2)
            self.GIF.delay = self.options.get("delay", 1.2)

    def stop_btn_pressed(self, *_):
        if self.GIF.is_animating:
            if not self.stopped:
                self.stop_gif()
                self.stopped = True
                self.root.ids.stop_btn.ripple_color = 0.25, 0.42, 0.25, 0.3
                self.root.ids.stop_btn.md_bg_color = 0.18, 0.36, 0.18, 1
                self.root.ids.stop_btn.line_color = 0.41, 0.75, 0.41, 1
                self.root.ids.stop_btn.icon_color = 0.75, 0.92, 0.75, 1
                self.root.ids.stop_btn.text = "Weiter"
            else:
                self.GIF.start_animation_schedule(target_screen=[self.root.ids.nav.children[1], "screen 1"],delay=self.options.get("delay", 1.2), instant=True)
                self.stopped = False
                self.root.ids.stop_btn.ripple_color = (1, 0, 0, 0.3)
                self.root.ids.stop_btn.md_bg_color = (0.686, 0.133, 0.133)
                self.root.ids.stop_btn.line_color = "orange"
                self.root.ids.stop_btn.icon_color = "orange"
                self.root.ids.stop_btn.text = "Stop"


Client = LateinVerbenApp()
Client.run()
