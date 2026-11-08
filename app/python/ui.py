
import json
import tkinter as tk
from tkinter import ttk, messagebox


# ============================================================
# KONFIGURACJA
# ============================================================

RESOLUTIONS = {
    "H3-7": 7,
    "H3-8": 8,
    "H3-9": 9,
}

BACKGROUND = "#f1f3f5"
BORDER_COLOR = "#777777"


# ============================================================
# KOLORY WSKAZNIKA IOP
# ============================================================

def iop_color(value):
    """
    -1 = czerwony
     0 = bialy
    +1 = zielony
    """

    value = max(-1.0, min(1.0, float(value)))

    if value < 0:
        t = value + 1.0
        r = 255
        g = round(255 * t)
        b = round(255 * t)
    else:
        t = value
        r = round(255 * (1 - t))
        g = 255
        b = round(255 * (1 - t))

    return f"#{r:02x}{g:02x}{b:02x}"


# ============================================================
# ODCZYT GEOMETRII GEOJSON
# ============================================================

def get_polygons(geometry):
    """
    Zwraca zewnetrzne pierscienie polygonow.
    Obsluguje Polygon i MultiPolygon.

    W obecnej wizualizacji nie rysujemy otworow
    wewnetrznych polygonow.
    """

    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]

    if geometry["type"] == "MultiPolygon":
        return [
            polygon[0]
            for polygon in geometry["coordinates"]
        ]

    return []


# ============================================================
# APLIKACJA TKINTER
# ============================================================

class IOPApplication:

    def __init__(self, root):

        self.root = root
        self.root.title(
            "Analiza przejezdnosci terenu - BDOT10k / H3"
        )
        self.root.geometry("1300x800")
        self.root.minsize(900, 600)

        self.features = []
        self.item_lookup = {}

        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        self.drag_start = None
        self.last_mouse = None
        self.dragged = False

        self.selected_id = None

        self.create_interface()

    # ========================================================
    # INTERFEJS
    # ========================================================

    def create_interface(self):

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 10))

        ttk.Label(
            header,
            text="Analiza przejezdnosci terenu",
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text=(
                "Wizualizacja wskaznika IOP "
                "na siatce heksagonalnej H3"
            ),
        ).pack(anchor="w")

        content = ttk.Frame(main)
        content.pack(fill="both", expand=True)

        sidebar = ttk.Frame(content, width=280)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)

        self.create_sidebar(sidebar)

        map_area = ttk.Frame(content)
        map_area.pack(side="right", fill="both", expand=True)

        self.canvas = tk.Canvas(
            map_area,
            background=BACKGROUND,
            highlightthickness=1,
            highlightbackground="#cccccc",
        )
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)

        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", self.on_zoom)
        self.canvas.bind("<Button-5>", self.on_zoom)

        self.status = tk.StringVar(
            value="Gotowe. Polacz sie z baza danych."
        )

        ttk.Label(
            main,
            textvariable=self.status,
            anchor="w",
            padding=(5, 8),
        ).pack(fill="x")

    # ========================================================
    # PANEL BOCZNY
    # ========================================================

    def create_sidebar(self, parent):

        db_frame = ttk.LabelFrame(
            parent,
            text="Polaczenie z PostGIS",
            padding=10,
        )
        db_frame.pack(fill="x", pady=(0, 12))

        self.host = tk.StringVar(value="localhost")
        self.port = tk.StringVar(value="5444")
        self.database = tk.StringVar(value="psip")
        self.username = tk.StringVar(value="psip")
        self.password = tk.StringVar()

        fields = [
            ("Host", self.host),
            ("Port", self.port),
            ("Baza", self.database),
            ("Uzytkownik", self.username),
        ]

        for label, variable in fields:

            ttk.Label(
                db_frame,
                text=label,
            ).pack(anchor="w")

            ttk.Entry(
                db_frame,
                textvariable=variable,
            ).pack(fill="x", pady=(0, 6))

        ttk.Label(
            db_frame,
            text="Haslo",
        ).pack(anchor="w")

        ttk.Entry(
            db_frame,
            textvariable=self.password,
            show="*",
        ).pack(fill="x", pady=(0, 5))

        selection_frame = ttk.LabelFrame(
            parent,
            text="Rozdzielczosc H3",
            padding=10,
        )
        selection_frame.pack(fill="x", pady=(0, 12))

        self.resolution = tk.StringVar(value="H3-7")

        self.resolution_box = ttk.Combobox(
            selection_frame,
            textvariable=self.resolution,
            values=list(RESOLUTIONS),
            state="readonly",
        )
        self.resolution_box.pack(fill="x", pady=(0, 8))

        ttk.Button(
            selection_frame,
            text="Wczytaj wyniki",
            command=self.load_data,
        ).pack(fill="x")

        ttk.Button(
            selection_frame,
            text="Dopasuj mape",
            command=self.fit_map,
        ).pack(fill="x", pady=(8, 0))

        self.create_legend(parent)
        self.create_details(parent)

    # ========================================================
    # LEGENDA
    # ========================================================

    def create_legend(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Legenda przejezdnosci",
            padding=10,
        )
        frame.pack(fill="x", pady=(0, 12))

        legend = tk.Canvas(
            frame,
            width=240,
            height=40,
            highlightthickness=0,
        )
        legend.pack(fill="x")

        width = 240

        for x in range(width):

            value = -1 + 2 * x / (width - 1)

            legend.create_line(
                x, 0,
                x, 20,
                fill=iop_color(value),
            )

        legend.create_text(
            3, 30,
            text="-1",
            anchor="w",
        )

        legend.create_text(
            width / 2, 30,
            text="0",
        )

        legend.create_text(
            width - 3, 30,
            text="+1",
            anchor="e",
        )

        ttk.Label(
            frame,
            text=(
                "Czerwony: utrudniona przejezdnosc\n"
                "Bialy: wynik neutralny\n"
                "Zielony: korzystna przejezdnosc"
            ),
            justify="left",
        ).pack(anchor="w", pady=(7, 0))

    # ========================================================
    # INFORMACJE O HEKSAGONIE
    # ========================================================

    def create_details(self, parent):

        frame = ttk.LabelFrame(
            parent,
            text="Wybrany heksagon",
            padding=10,
        )
        frame.pack(fill="x")

        self.details = tk.StringVar(
            value="Kliknij heksagon na mapie."
        )

        ttk.Label(
            frame,
            textvariable=self.details,
            justify="left",
            wraplength=240,
        ).pack(anchor="w")

    # ========================================================
    # POBRANIE DANYCH Z POSTGIS
    # ========================================================

    def load_data(self):

        try:
            import psycopg2
        except ImportError:
            messagebox.showerror(
                "Brak biblioteki",
                "Zainstaluj biblioteke psycopg2-binary "
                "w interpreterze Python uzywanym "
                "przez PyCharm.",
            )
            return

        resolution = RESOLUTIONS[self.resolution.get()]
        table = f"grid.h3_r{resolution}"

        self.status.set(
            f"Wczytywanie danych H3-{resolution}..."
        )
        self.root.update_idletasks()

        connection = None

        try:
            connection = psycopg2.connect(
                host=self.host.get().strip(),
                port=int(self.port.get()),
                dbname=self.database.get().strip(),
                user=self.username.get().strip(),
                password=self.password.get(),
                connect_timeout=10,
            )

            # Baza danych tylko do odczytu.
            connection.set_session(
                readonly=True,
                autocommit=True,
            )

            with connection.cursor() as cursor:

                cursor.execute(f"""
                    SELECT
                        h3_id,
                        wsp_iop_norm,
                        liczba_klas_iop,
                        ST_AsGeoJSON(
                            ST_Transform(geom, 2180),
                            3
                        )
                    FROM {table}
                    ORDER BY h3_id
                """)

                rows = cursor.fetchall()

        except Exception as error:

            messagebox.showerror(
                "Blad PostGIS",
                str(error),
            )

            self.status.set(
                "Nie udalo sie wczytac danych."
            )
            return

        finally:
            if connection is not None:
                connection.close()

        features = []

        for h3_id, iop, classes, geom_json in rows:

            if geom_json is None:
                continue

            geometry = json.loads(geom_json)
            polygons = get_polygons(geometry)

            if not polygons:
                continue

            points = [
                (float(x), float(y))
                for polygon in polygons
                for x, y in polygon
            ]

            if not points:
                continue

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]

            features.append({
                "id": str(h3_id),
                "iop": float(iop) if iop is not None else None,
                "classes": classes,
                "polygons": polygons,
                "bbox": (
                    min(xs), min(ys),
                    max(xs), max(ys),
                ),
            })

        self.features = features
        self.selected_id = None

        self.details.set(
            "Kliknij heksagon na mapie."
        )

        self.status.set(
            f"Wczytano {len(features)} heksagonow "
            f"dla H3-{resolution}."
        )

        self.root.after(100, self.fit_map)

    # ========================================================
    # DOPASOWANIE MAPY
    # ========================================================

    def fit_map(self):

        if not self.features:
            return

        min_x = min(
            feature["bbox"][0]
            for feature in self.features
        )
        min_y = min(
            feature["bbox"][1]
            for feature in self.features
        )
        max_x = max(
            feature["bbox"][2]
            for feature in self.features
        )
        max_y = max(
            feature["bbox"][3]
            for feature in self.features
        )

        width = max(self.canvas.winfo_width(), 100)
        height = max(self.canvas.winfo_height(), 100)

        span_x = max(max_x - min_x, 1)
        span_y = max(max_y - min_y, 1)

        self.scale = min(
            width * 0.90 / span_x,
            height * 0.90 / span_y,
        )

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        self.offset_x = (
            width / 2 - center_x * self.scale
        )
        self.offset_y = (
            height / 2 + center_y * self.scale
        )

        self.draw_map()

    # ========================================================
    # PRZEKSZTALCENIE WSPOLRZEDNYCH
    # ========================================================

    def world_to_screen(self, x, y):

        screen_x = x * self.scale + self.offset_x
        screen_y = -y * self.scale + self.offset_y

        return screen_x, screen_y

    # ========================================================
    # RYSOWANIE MAPY
    # ========================================================

    def draw_map(self):

        self.canvas.delete("all")
        self.item_lookup = {}

        if not self.features:
            return

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        for feature in self.features:

            min_x, min_y, max_x, max_y = feature["bbox"]

            sx1, sy1 = self.world_to_screen(
                min_x, max_y
            )
            sx2, sy2 = self.world_to_screen(
                max_x, min_y
            )

            # Pomijamy obiekty poza aktualnym widokiem.
            if (
                sx2 < 0 or sx1 > width
                or sy2 < 0 or sy1 > height
            ):
                continue

            iop = feature["iop"]

            if iop is None:
                fill = "#aaaaaa"
            else:
                fill = iop_color(iop)

            selected = (
                feature["id"] == self.selected_id
            )

            for polygon in feature["polygons"]:

                coords = []

                for x, y in polygon:
                    sx, sy = self.world_to_screen(x, y)
                    coords.extend((sx, sy))

                if len(coords) < 6:
                    continue

                item_id = self.canvas.create_polygon(
                    coords,
                    fill=fill,
                    outline=(
                        "#111111"
                        if selected
                        else BORDER_COLOR
                    ),
                    width=3 if selected else 0.4,
                    tags=("hex",),
                )

                self.item_lookup[item_id] = feature

        if self.selected_id:
            self.canvas.tag_raise("selected")

    # ========================================================
    # WYBIERANIE HEKSAGONU
    # ========================================================

    def select_hexagon(self, x, y):

        items = self.canvas.find_overlapping(
            x, y, x, y
        )

        for item_id in reversed(items):

            feature = self.item_lookup.get(item_id)

            if feature is None:
                continue

            self.selected_id = feature["id"]

            iop = feature["iop"]

            if iop is None:
                iop_text = "brak danych"
            else:
                iop_text = f"{iop:+.2f}"

            self.details.set(
                f"H3 ID: {feature['id']}\n"
                f"IOP: {iop_text}\n"
                f"Liczba klas BDOT10k: "
                f"{feature['classes']}"
            )

            self.draw_map()
            return

    # ========================================================
    # PRZESUWANIE MAPY
    # ========================================================

    def on_press(self, event):

        self.drag_start = (event.x, event.y)
        self.last_mouse = (event.x, event.y)
        self.dragged = False

    def on_drag(self, event):

        if self.last_mouse is None:
            return

        last_x, last_y = self.last_mouse

        dx = event.x - last_x
        dy = event.y - last_y

        if self.drag_start is not None:
            start_x, start_y = self.drag_start

            if (
                abs(event.x - start_x) > 4
                or abs(event.y - start_y) > 4
            ):
                self.dragged = True

        self.offset_x += dx
        self.offset_y += dy

        self.canvas.move("hex", dx, dy)

        self.last_mouse = (event.x, event.y)

    def on_release(self, event):

        if not self.dragged:
            self.select_hexagon(event.x, event.y)

        self.drag_start = None
        self.last_mouse = None
        self.dragged = False

    # ========================================================
    # PRZYBLIZANIE I ODDALANIE
    # ========================================================

    def on_zoom(self, event):

        if not self.features:
            return

        if getattr(event, "num", None) == 4:
            factor = 1.2

        elif getattr(event, "num", None) == 5:
            factor = 1 / 1.2

        elif event.delta > 0:
            factor = 1.2

        else:
            factor = 1 / 1.2

        new_scale = self.scale * factor

        if not 0.000001 <= new_scale <= 1000:
            return

        # Zachowujemy pozycje kursora podczas zoomu.

        self.offset_x = (
            event.x
            - (event.x - self.offset_x) * factor
        )

        self.offset_y = (
            event.y
            - (event.y - self.offset_y) * factor
        )

        self.scale = new_scale

        self.draw_map()


# ============================================================
# START APLIKACJI
# ============================================================

def main():

    root = tk.Tk()
    IOPApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()
