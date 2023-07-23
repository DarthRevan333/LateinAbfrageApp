import requests
import json
import random
from bs4 import BeautifulSoup
from threading import Thread, current_thread
from time import sleep
from urllib.parse import urljoin


class ThreadLimiter:
    """Convenience class for limiting the maximum amount of threads executing certain tasks"""

    def __init__(self, tasks: list, args: list, max_threads: int, on_finish=None, allow_empty_tasks: bool = False):
        """
        :param tasks: Thread tasks (which will immediately be run on initialization)
        :param args: Arguments corresponding to thread tasks (defaults to [], which represents no arguments)
        :param max_threads: Maximum amount of threads this class should run (Note that it runs an additional manage thread)
        :param on_finish: Optional on_finish callback run on the manage thread
        :param allow_empty_tasks: Allow the initialization of the class without starting the tasks due to having none
        :return: Runs multiple tasks threaded with a given limit of how much should run at the same time
        """
        self.current_threads = []
        self.allow_empty = allow_empty_tasks
        if tasks and max_threads > 0:
            self.tasks = tasks
            self.args = args if args else [[] for _ in range(len(self.tasks))]
            self.max_threads = max_threads
            self.managed = False
            self.active = True
            self.on_finish = on_finish
            Thread(target=self.manage).start()
        elif (not tasks and not self.allow_empty) or max_threads < 0:
            raise ValueError("Parameter tasks must not be empty" if not tasks else "Parameter max_threads must be greater than 0")
        else:
            self.active = False

    def restart(self) -> None:
        """
        This should be called if the __init__ method allowed the emptiness of the tasks parameter and therefore did
        not start the manage thread along with the tasks to be threaded

        :return: Calls a certain part of the __init__ method for setup and then restarts the execution of tasks
        """
        if self.tasks:
            self.args = self.args if self.args else [[] for _ in range(len(self.tasks))]
            self.managed = False
            self.active = True
            Thread(target=self.manage).start()
        elif (not self.tasks and not self.allow_empty) or self.max_threads < 0:
            raise ValueError(
                "tasks must not be empty" if not self.tasks else "max_threads must be greater than 0")
        else:
            self.active = False

    def manage(self) -> None:
        """
        :return: Manages the currently running threads and starts new ones once old ones have finished executing
        """
        for i, (task, args) in enumerate(zip(self.tasks, self.args)):
            if len([t for t in self.current_threads if t.is_alive()]) < self.max_threads:
                if i != len(self.tasks)-1:
                    T = Thread(target=task, args=(*args,))
                    T.start()
                    self.current_threads.append(T)
                else:
                    self.current_threads.append(current_thread())
                    task(*args)
                    self.current_threads.remove(current_thread())
                self.managed = True
            else:
                while len([t for t in self.current_threads if t.is_alive()]) == self.max_threads:
                    sleep(0.05)
        self.join()
        if self.on_finish is not None:
            self.on_finish()
        self.active = False
        self.tasks.clear()
        self.args.clear()

    def join(self, checking_delay: int = 0.05) -> None:
        """
        :param checking_delay: The delay to wait between calling the is_alive() method of all running threads
        :return: Waits until the is_alive() method of all running threads returns False indicating they have finished
        """
        while bool([t for t in self.current_threads if t.is_alive()]) or not self.managed:
            sleep(checking_delay)


class VerbenScraper:
    def __init__(self):
        self.base_address = "https://www.frag-caesar.de/lateinwoerterbuch/"
        self.base_address_extension = "-uebersetzung.html"
        self.headers = {
            'authority': 'www.frag-caesar.de',
            'accept': 'text/html',
            'accept-language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'max-age=0',
            'dnt': '1',
            'referer': 'https://www.frag-caesar.de/lateinwoerterbuch/damnare-uebersetzung.html',
            'sec-ch-ua': '"Opera GX";v="99", "Chromium";v="113", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'sec-gpc': '1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36 OPR/99.0.0.0'
        }
        self.data = self.load_data()
        self.session = requests.session()
        self.failures = []
        self.success = []

    def get_data(self, verb_base: str, exclude_supina: bool = False) -> dict:
        response = self.session.get(f"{self.base_address}{verb_base}{self.base_address_extension}", headers=self.headers)
        soup = BeautifulSoup(response.text, "html.parser")

        if (selection := soup.find("div", attrs={"id": "testimonials-1"})) is not None:
            all_verb_options = [sel for sel in selection.find_all("li", attrs={"class": "list-group-item list-toggle"})
                                if sel.find("span", attrs={"class": "badge badge-orange rounded badge-wordtype"}).text == "Verb"]
            if all_verb_options:
                response = self.session.get(urljoin(self.base_address, all_verb_options[0].find("a").attrs["href"]),
                                            headers=self.headers)
                soup = BeautifulSoup(response.text, "html.parser")
            else:
                return {}
        try:
            title_translation_dict = {"Imperative": "Imperativ", "Infinite": "Infinitiv"}
            content = [child for child in soup.find("div", attrs={"id": "vtab-1"}).children if not child.text == "\n"]
            grouped_content = {title_translation_dict.get(a.text, a.text): self.extract_from_toggle_element(b) for a, b in zip(content[::2], content[1::2])}
            if exclude_supina:
                if "Supina" in grouped_content.keys():
                    del grouped_content["Supina"]
            else:
                grouped_content.update({"Supina": dict(zip(*grouped_content.get("Supina").items()))})
            try:
                grouped_content.update({"Gerundivum": grouped_content.get("Gerundivum").get("PPP")})
                grouped_content.update({"Imperativ": {"Imperativ I": grouped_content.get("Imperativ").get("Aktiv"),
                                        "Imperativ II": grouped_content.get("Imperativ").get("Passiv")}})
            finally:
                return {soup.find("div", attrs={"class": "table-responsive"}).find("td", attrs={"class": "eh2"}).text: grouped_content}
        except Exception:
            return {}

    def multi_update_data(self, new_words: list, exclude_supina: bool = False, save: bool = True, joining: bool = True) -> ThreadLimiter:
        Limiter = ThreadLimiter([self.update_data for _ in range(len(new_words))], [[word.strip(), exclude_supina] for word in new_words], 10, on_finish=lambda *_: self.multi_update_on_finish_callback(save))
        if joining:
            Limiter.join()
        return Limiter

    def multi_update_on_finish_callback(self, saving: bool):
        if saving:
            self.save_data()

    def update_data(self, verb_base: str, exclude_supina: bool = False, save: bool = False) -> None:
        try:
            new_data = self.get_data(verb_base, exclude_supina=exclude_supina)
            if new_data:
                self.success.append(list(new_data.keys())[0])
                self.data.update(new_data)
                if save:
                    self.save_data()
            else:
                self.failures.append(verb_base)
        except Exception:
            self.failures.append(f"{verb_base}(Verbindungsfehler)")

    def extract_from_toggle_element(self, element) -> dict:
        tables = element.find_all("table")
        special_table = tables[0].find("tr").text.strip().replace("\n", "") == "MaskulinumFemininumNeutrum"
        infinitive_table_counter = 0
        found = {"Aktiv": {}, "Passiv": {}} if not special_table else {"PPP": {"Singular": {}, "Plural": {}},
                                                                       "PPA": {"Singular": {}, "Plural": {}},
                                                                       "PFA": {"Singular": {}, "Plural": {}}}
        for i, table in enumerate(tables):
            if not special_table:
                for tr in table.find_all("tr"):
                    if tr.text.strip().replace("\n", "") not in ["Passiv", "LateinDeutsch", "Latein", "Aktiv", "Supin I	Supin II", ]:
                        tds = tr.find_all("td")
                        try:
                            found.get("Aktiv" if not i and not infinitive_table_counter else "Passiv").update({tds[0].text: self.__get_td_text(tds[1])})
                        except AttributeError:
                            found.get("Aktiv" if not i and not infinitive_table_counter else "Passiv").update({tds[0].text: tds[1].text})
                    elif len(tables) == 1 and tr.text.strip().replace("\n", "") == "Passiv":
                        infinitive_table_counter += 1
            else:
                for tr in table.find_all("tr"):
                    if tr.text.strip().replace("\n", "") not in ["Passiv", "LateinDeutsch", "Latein", "Aktiv",
                                                                 "MaskulinumFemininumNeutrum"]:
                        tds = tr.find_all("td")
                        try:
                            found.get("PPP" if i < 2 else "PPA" if i < 4 else "PFA").get("Singular" if not i % 2 else "Plural").update(
                                {tds[0].text: {"Maskulinum": self.__get_td_text(tds[1]),
                                               "Femininum": self.__get_td_text(tds[2]),
                                                "Neutrum": self.__get_td_text(tds[3])}})
                        except AttributeError:
                            found.get("PPP" if i < 2 else "PPA" if i < 4 else "PFA").get(
                                "Singular" if not i % 2 else "Plural").update(
                                {tds[0].text: {"Maskulinum": tds[1].text,
                                               "Femininum": tds[2].text,
                                               "Neutrum": tds[3].text}})
        return found if special_table or found.get("Passiv") else found.get("Aktiv")

    @staticmethod
    def __get_td_text(element) -> str:
        if len(element.find_all("span", attrs={"class": "f"})) == 1:
            return element.text
        else:
            return element.find("span", attrs={"class": "f"}).text

    @staticmethod
    def load_data() -> dict:
        try:
            with open("./data.json", "r") as data_file:
                try:
                    data = json.load(data_file)
                except Exception:
                    data = {}
            return {} if not data else data if "options" not in data.keys() and "data" not in data.keys() else data.get("data")
        except FileNotFoundError:
            return {}

    def save_data(self) -> None:
        with open("./data.json", "w") as data_file:
            json.dump(self.data, data_file)

    def get_random_question(self, exclude_tense: list = 'Defaults to ["Supina"]', ignore_gender_parti: bool = False,
                            ignore_gender_gerundivum: bool = False, exclude_imperativ_2: bool = True,
                            exclude_non_existing: bool = True, ask_question_with_input: bool = False, weights="relevant",
                            exclude_choice: list = None) -> tuple:
        """
        :param exclude_tense: Which tenses to exclude
        :param ignore_gender_parti: Ignore gender for participles
        :param ignore_gender_gerundivum: Ignore gender for gerundivum
        :param exclude_imperativ_2: Only ask about the Imperativ I (exclude Imperative II)
        :param exclude_non_existing: Whether to exclude questions that don't have an answer
        :param weights: Weights for the random selection of tenses (list of ints with len 16). Presets: 'relevant', 'basic', 'gerund', 'partizip', 'special', 'supina'
        :param ask_question_with_input: Whether to enter an interactive (question -> user input -> solution)-state?
        :param exclude_choice: Which words to exclude
        :return: A tuple with the question (str) at index 0 and the answer(s) (list -> multiple or str -> one) at index 1
        """
        question = self.__get_random_question(exclude_tense, ignore_gender_parti, ignore_gender_gerundivum, exclude_imperativ_2, weights, exclude_choice=exclude_choice)
        while ("existiert nicht" in question[1] or not all(question)) and exclude_non_existing:
            question = self.__get_random_question(exclude_tense, ignore_gender_parti, ignore_gender_gerundivum,
                                                  exclude_imperativ_2, exclude_choice=exclude_choice)
        if ask_question_with_input:
            self.ask_question(*question)
        if "Imperativ Imperativ" in question[0]:
            question = (question[0].replace("Imperativ Imperativ", "Imperativ"), question[1])
        return question

    def __get_random_question(self, exclude_tense: list = 'Defaults to ["Supina"]', ignore_gender_parti: bool = False,
                              ignore_gender_gerundivum: bool = False, exclude_imperativ_2: bool = True, weights="relevant",
                              exclude_choice: list = None) -> tuple:
        """
        :param exclude_tense: Which tenses to exclude
        :param ignore_gender_parti: Ignore gender for participles
        :param ignore_gender_gerundivum: Ignore gender for gerundivum
        :param exclude_imperativ_2: Only ask about the Imperativ I (exclude Imperative II)
        :param weights: Weights for the random selection of tenses (list of ints with len 16). Presets: 'relevant', 'basic', 'gerund', 'partizip', 'special', 'supina'
        :param exclude_choice: Which words to exclude
        :return: A tuple with the question (str) at index 0 and the answer(s) (list -> multiple or str -> one) at index 1
        """
        if exclude_tense == 'Defaults to ["Supina"]':
            exclude_tense = ["Supina"]
        if isinstance(weights, str):
            if (w := weights.lower()) == "relevant":
                weights = [6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 6.5, 4, 3, 4, 6.5, 14.5, 3]
            elif w == "zeiten":
                weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
            elif w == "basic":
                weights = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0]
            elif w.startswith("gerund"):
                weights = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0]
            elif w.startswith("partizip"):
                weights = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0]
            elif w in ["special", "spezial", "abwandlungen"]:
                weights = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 3, 0]
            elif w == "supina":
                weights = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
            else:
                raise ValueError(f"Got invalid preset for weights: {weights}")
        elif not isinstance(weights, list) or (len(weights) != 16 and
                                               ("supina" not in exclude_tense and "Supina" not in exclude_tense)):
            raise ValueError("Invalid value for weights was given")
        elif ("supina" in exclude_tense or "Supina" in exclude_tense) and len(weights) != 15:
            raise ValueError("Invalid length for weights")
        elif ("supina" in exclude_tense or "Supina" in exclude_tense) and len(weights) == 15:
            weights.append(0)
        choice = random.choices(list(self.data.keys()))[0]
        while exclude_choice is not None and choice in exclude_choice:
            choice = random.choices(list(self.data.keys()))[0]
        tense = random.choices(list(self.data.get(choice).keys()), weights=weights)[0]
        while tense in exclude_tense:
            tense = random.choices(list(self.data.get(choice).keys()), weights=weights)[0]
        if exclude_imperativ_2 and tense == "Imperativ":
            person = random.choices(list(self.data.get(choice).get(tense).get("Imperativ I").keys()))[0]
            return f"Was ist {tense} {person} von {choice}? ", self.data.get(choice).get(tense).get("Imperativ I").get(person)
        elif tense not in ["Gerundium", "Gerundivum", "Partizipien", "Supina"]:
            voice = random.choices(list(self.data.get(choice).get(tense).keys()))[0]
            person = random.choices(list(self.data.get(choice).get(tense).get(voice).keys()))[0]
            return f"Was ist {tense} {voice} {person} von {choice}? ", self.data.get(choice).get(tense).get(voice).get(person)
        elif tense in ["Gerundium", "Supina"]:
            time_or_case = random.choices(list(self.data.get(choice).get(tense).keys()))[0]
            return f"Was ist {tense} {time_or_case} von {choice}? ", self.data.get(choice).get(tense).get(time_or_case)
        elif tense == "Gerundivum":
            mode = random.choices(list(self.data.get(choice).get(tense).keys()))[0]
            case = random.choices(list(self.data.get(choice).get(tense).get(mode).keys()))[0]
            if not ignore_gender_gerundivum:
                gender = random.choices(list(self.data.get(choice).get(tense).get(mode).get(case).keys()))[0]
                return f"Was ist {tense} {mode} {case} {gender} von {choice}? ", self.data.get(choice).get(tense).get(mode).get(case).get(gender)
            else:
                return f"Was ist {tense} {mode} {case} von {choice}? ", [(c := self.data.get(choice).get(tense).get(mode).get(case)).get("Maskulinum"), c.get("Femininum"), c.get("Neutrum")]
        elif tense == "Partizipien":
            P_type = random.choices(list(self.data.get(choice).get(tense).keys()))[0]
            mode = random.choices(list(self.data.get(choice).get(tense).get(P_type).keys()))[0]
            case = random.choices(list(self.data.get(choice).get(tense).get(P_type).get(mode).keys()))[0]
            if not ignore_gender_parti:
                gender = random.choices(list(self.data.get(choice).get(tense).get(P_type).get(mode).get(case).keys()))[0]
                return f"Was ist {P_type} {mode} {case} {gender} von {choice}? ", self.data.get(choice).get(tense).get(P_type).get(mode).get(case).get(gender)
            else:
                return f"Was ist {P_type} {mode} {case} von {choice}? ", [(c := self.data.get(choice).get(tense).get(P_type).get(mode).get(case)).get("Maskulinum"), c.get("Femininum"), c.get("Neutrum")]

    def search_in_data(self, choice: str, tense: str, voice: str, person: str) -> str:
        choice = choice.strip().replace("  ", " ")
        tense = " ".join([{"Imp": "Imperfekt", "Perf": "Perfekt", "Fut": "Futur", "1": "I", "2": "II", "Präs":
            "Präsens", "Prä": "Präsens", "Per": "Perfekt", "Plus": "Plusquamperfekt", "Plusquam": "Plusquamperfekt",
            "Plusquamperf": "Plusquamperfekt", "Gerundiv": "Gerundivum", "Ind": "Indikativ", "Konj":
            "Konjunktiv", "Kon": "Konjunktiv", "Fut1": "Futur I", "Fut2": "Futur II", "FutII": "Futur II",
            "FutI": "Futur I", "FuturI": "Futur I", "FuturII": "Futur II", "Futur1": "Futur I", "Futur2": "Futur II"}
                         .get(x.strip().rstrip('.'), x.strip()) for x in tense.split(sep=" ")]).replace("  ", " ")
        voice = {"Pass": "Passiv", "Passive": "Passiv", "Akt": "Aktiv", "Aktive": "Aktiv"}.get(voice.strip().rstrip("."), voice.strip()).replace("  ",  " ")
        person = " ".join([{"Zweite": "2.", "Dritte": "3.", "Erste": "1.", "Pers.": "Person", "Pers": "Person",
                  "Sing": "Singular", "Plur": "Plural", "Plu": "Plural", "P.": "Person", "P": "Person",
                  "S": "Singular", "Pl": "Plural", "2": "2.", "3": "3.", "1": "1."}.get(x.strip().rstrip("."), x.strip()) for x in person.split(sep=" ")]).replace("  ", " ")
        return self.data.get(choice.strip()).get(tense.strip()).get(voice.strip()).get(person.strip())

    def search(self, inpt: str) -> str:
        split = inpt.strip().replace(".", " ").replace("  ", " ").split(sep=" ")
        if len(split) > 5:
            return self.search_in_data(choice=split[0], tense=" ".join(split[1:3]), voice=split[3],
                                       person=" ".join(split[4:]))
        elif len(split) == 5:
            return self.search_in_data(choice=split[0], tense=" ".join(split[1]), voice=split[2],
                                       person=" ".join(split[3:]))

    def assert_data_contains(self, word_list: list, save: bool = True, exclude_supina: bool = False,
                             joining: bool = True) -> ThreadLimiter:
        if remaining_words := [word.strip() for word in word_list if word.strip() not in self.data.keys()]:
            return self.multi_update_data(remaining_words, save=save, exclude_supina=exclude_supina, joining=joining)
        else:
            return ThreadLimiter([], [], 1, allow_empty_tasks=True)

    def refresh_all(self, save: bool = True, exclude_supina: bool = False, joining: bool = True):
        to_refresh = list(self.data.keys())
        self.multi_update_data(to_refresh, exclude_supina=exclude_supina, joining=joining, save=save)

    def ask_question(self, question: str, correct_answer: str) -> None:
        inpt = input(question).strip().lower()
        if isinstance(correct_answer, str):
            if inpt != correct_answer.lower():
                print(f"Falsch! Die richtige Antwort wäre gewesen: {correct_answer}")
            else:
                print("Richtig!")
        elif inpt not in correct_answer:
            print(f"Falsch! Folgende Antworten wären richtig gewesen: {', '.join(correct_answer)}")
        else:
            print("Richtig!")

    def ask_random_question(self, exclude_tense: list = 'Defaults to ["Supina"]', ignore_gender_parti: bool = False,
                            ignore_gender_gerundivum: bool = False, exclude_imperativ_2: bool = True,
                            exclude_non_existing: bool = True, weights="relevant") -> None:
        """
        :param exclude_tense: Which tenses to exclude (this defaults to a list with only 'Supina' as its element)
        :param ignore_gender_parti: Ignore gender for participles
        :param ignore_gender_gerundivum: Ignore gender for gerundivum
        :param exclude_imperativ_2: Only ask about the Imperativ I (exclude Imperative II)
        :param exclude_non_existing: Whether to exclude questions that don't have an answer
        :param weights: Weights for the random selection of tenses (list of ints with len 16). Presets: 'relevant', 'basic', 'gerund', 'partizip', 'special', 'supina'
        :return: Asks a question in an interactive (question -> user input -> answer)-mode
        """
        self.get_random_question(exclude_tense=exclude_tense, ignore_gender_parti=ignore_gender_parti,
                                 ignore_gender_gerundivum=ignore_gender_gerundivum, ask_question_with_input=True,
                                 exclude_imperativ_2=exclude_imperativ_2, exclude_non_existing=exclude_non_existing,
                                 weights=weights)

    def test_random_questions(self, number: int = 200, print_out: bool = False):
        if not print_out:
            for _ in range(number):
                self.get_random_question()
        else:
            for _ in range(number):
                print(self.get_random_question())

    @property
    def currently_contained(self) -> list:
        return list(self.data.keys())


if __name__ == '__main__':
    Scraper = VerbenScraper()
    Scraper.assert_data_contains(["esse"])
    try:
        print("Testing 200 random questions...")
        Scraper.test_random_questions(print_out=True)
        print("Successfully tested 200 questions\n\n")
    except Exception as e:
        print(f"Failed with exception: {str(e)}")

    while True:
        Scraper.ask_random_question()
