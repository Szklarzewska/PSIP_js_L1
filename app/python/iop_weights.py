
# ============================================================
# MACIERZ WAG IVRF - BDOT10k
# WERSJA 3 - ZASADY POKONIECZNY (2018)
#
# Analiza przejezdnosci dla pojazdow wojskowych
# Obszar: powiat chelminski
#
# Z - waga zachowana z opracowania Pokoniecznego
# P - waga proponowana ekspercko
# N - obiekt neutralny lub niejednoznaczny
#
# Wagi dotycza klas, a nie pojedynczych obiektow.
# ============================================================

WAGI_IVRF = [

    # ========================================================
    # 1. POKRYCIE TERENU
    # ========================================================

    ("ot_ptgn_a",  0.20, "P",
     "Grunty nieuzytkowane - potencjalnie otwarte"),

    ("ot_ptkm_a",  0.60, "P",
     "Tereny komunikacyjne - sprzyjaja przemieszczaniu"),

    ("ot_ptlz_a", -0.80, "Z",
     "Lasy i zadrzewienia - przeszkoda dla pojazdow"),

    ("ot_ptnz_a",  0.50, "P",
     "Tereny niezabudowane - teren potencjalnie przejezdny"),

    ("ot_ptpl_a",  0.70, "P",
     "Place - powierzchnie manewrowe"),

    ("ot_ptrk_a", -0.60, "P",
     "Roslinnosc krzewiasta - ogranicza przejazd"),

    ("ot_ptso_a", -0.85, "P",
     "Skladowiska odpadow - przeszkody i niestabilne podloze"),

    ("ot_pttr_a",  0.60, "P",
     "Trawy i uprawy rolne - teren otwarty"),

    ("ot_ptut_a", -0.40, "P",
     "Uprawy trwale - nasadzenia utrudniaja przejazd"),

    ("ot_ptwp_a", -1.00, "Z",
     "Wody powierzchniowe - bariera terenowa"),

    ("ot_ptwz_a", -0.85, "P",
     "Wyrobiska i zwalowiska - trudny teren"),

    ("ot_ptzb_a", -0.75, "P",
     "Tereny zabudowane - ograniczenie przejezdnosci"),


    # ========================================================
    # 2. SIEC KOMUNIKACYJNA
    # ========================================================

    ("ot_skdr_l",  0.70, "Z",
     "Drogi - ulatwiaja ruch pojazdow"),

    ("ot_skjz_l",  0.00, "N",
     "Jezdnie - mozliwe powielanie warstwy drog"),

    ("ot_skpp_l",  0.65, "P",
     "Przeprawy - ulatwiaja przekraczanie przeszkod"),

    ("ot_skrp_l",  0.30, "P",
     "Ciagi piesze i rowerowe - ograniczone ulatwienie"),

    ("ot_skrw_p",  0.40, "P",
     "Wezly komunikacyjne - ulatwienie lokalne"),

    ("ot_sktr_l", -0.50, "P",
     "Tory kolejowe - utrudnienie ruchu poprzecznego"),


    # ========================================================
    # 3. SIEC WODNA I UZBROJENIE
    # ========================================================

    ("ot_swkn_l", -0.90, "P",
     "Kanaly - przeszkody wodne"),

    ("ot_swrm_l", -0.60, "P",
     "Rowy melioracyjne - przeszkody liniowe"),

    ("ot_swrs_l", -0.90, "P",
     "Rzeki i strumienie - przeszkody wodne"),

    ("ot_suln_l",  0.00, "N",
     "Linie napowietrzne - niejednoznaczny wplyw"),

    ("ot_supr_l",  0.00, "N",
     "Przewody rurowe - wplyw zalezy od posadowienia"),


    # ========================================================
    # 4. BUDYNKI, BUDOWLE I URZADZENIA
    # ========================================================

    ("ot_bubd_a", -0.90, "P",
     "Budynki - silne przeszkody fizyczne"),

    ("ot_buhd_l", -0.60, "P",
     "Budowle hydrotechniczne - mozliwe bariery"),

    ("ot_buib_a", -0.50, "P",
     "Budowle powierzchniowe - przeszkody fizyczne"),

    ("ot_buib_l", -0.50, "P",
     "Budowle liniowe - mozliwe przeszkody"),

    ("ot_buin_l",  0.00, "N",
     "Budowle inzynierskie - rozne funkcje i wplyw"),

    ("ot_buit_a", -0.40, "P",
     "Urzadzenia techniczne powierzchniowe - przeszkody"),

    ("ot_buit_p",  0.00, "N",
     "Urzadzenia punktowe - brak zasiegu przeszkody"),

    ("ot_busp_a",  0.00, "N",
     "Budowle sportowe - wplyw zalezy od rodzaju"),

    ("ot_busp_l",  0.00, "N",
     "Budowle sportowe liniowe - niejednorodne"),

    ("ot_butr_l",  0.00, "N",
     "Urzadzenia transportowe - rozne funkcje"),

    ("ot_buuo_l", -0.70, "P",
     "Umocnienia - istotne przeszkody liniowe"),

    ("ot_buwt_p",  0.00, "N",
     "Wysokie budowle punktowe - lokalne obiekty"),

    ("ot_buzm_l", -0.75, "P",
     "Budowle ziemne - utrudnienia terenowe"),

    ("ot_buzt_a", -0.90, "P",
     "Zbiorniki techniczne powierzchniowe - bariera"),

    ("ot_buzt_p",  0.00, "N",
     "Zbiorniki punktowe - brak opisu zasiegu"),


    # ========================================================
    # 5. KOMPLEKSY UZYTKOWANIA TERENU
    # ========================================================

    ("ot_kuho_a",  0.00, "N",
     "Kompleks hotelarski - przeszkody opisane osobno"),

    ("ot_kuhu_a",  0.00, "N",
     "Kompleks handlowy - zroznicowana powierzchnia"),

    ("ot_kuko_a",  0.30, "P",
     "Kompleks komunikacyjny - ulatwienie ruchu"),

    ("ot_kuko_p",  0.00, "N",
     "Kompleks komunikacyjny punktowy - brak zasiegu"),

    ("ot_kuos_a",  0.00, "N",
     "Kompleks oswiatowy - funkcja nie okresla przejazdu"),

    ("ot_kuoz_a",  0.00, "N",
     "Kompleks zdrowia - funkcja nie okresla przejazdu"),

    ("ot_kupg_a", -0.35, "P",
     "Kompleks przemyslowy - czeste przeszkody terenowe"),

    ("ot_kupg_p",  0.00, "N",
     "Kompleks przemyslowy punktowy - brak zasiegu"),

    ("ot_kusc_a", -0.35, "P",
     "Cmentarze i kompleksy sakralne - ograniczenia"),

    ("ot_kusk_a",  0.20, "P",
     "Kompleks sportowy - potencjalne tereny otwarte"),

    ("ot_kuza_a",  0.00, "N",
     "Kompleks zabytkowy - niejednoznaczny wplyw"),


    # ========================================================
    # 6. OBIEKTY INNE I RZEZBA TERENU
    # ========================================================

    ("ot_oikm_a",  0.00, "N",
     "Obiekty komunikacyjne - niejednorodne"),

    ("ot_oikm_l",  0.00, "N",
     "Obiekty komunikacyjne liniowe - niejednorodne"),

    ("ot_oikm_p",  0.00, "N",
     "Obiekty komunikacyjne punktowe - niejednorodne"),

    ("ot_oimk_a", -1.00, "P",
     "Mokradla - bardzo niska przejezdnosc"),

    ("ot_oior_a",  0.00, "N",
     "Obiekty orientacyjne - funkcja informacyjna"),

    ("ot_oior_l",  0.00, "N",
     "Obiekty orientacyjne liniowe - informacyjne"),

    ("ot_oior_p",  0.00, "N",
     "Obiekty orientacyjne punktowe - informacyjne"),

    ("ot_oipr_l",  0.00, "N",
     "Obiekty przyrodnicze liniowe - niejednorodne"),

    ("ot_oipr_p",  0.00, "N",
     "Obiekty przyrodnicze punktowe - lokalne"),

    ("ot_oisz_a", -0.90, "P",
     "Szuwary - roslinnosc terenow podmoklych"),

    ("ot_rtlw_l",  0.00, "N",
     "Warstwice - informacja o rzezbie terenu"),

    ("ot_rtpw_p",  0.00, "N",
     "Punkty wysokosciowe - informacja o wysokosci"),


    # ========================================================
    # 7. ADMINISTRACJA I OCHRONA PRZYRODY
    # ========================================================

    ("ot_adja_a",  0.00, "N",
     "Jednostki administracyjne - granice umowne"),

    ("ot_adms_a",  0.00, "N",
     "Obszary miejscowosci - obiekt opisowy"),

    ("ot_adms_p",  0.00, "N",
     "Punkty miejscowosci - obiekt lokalizacyjny"),

    ("ot_tcon_a",  0.00, "N",
     "Natura 2000 - status ochronny"),

    ("ot_tcpk_a",  0.00, "N",
     "Parki krajobrazowe - status ochronny"),

    ("ot_tcpn_a",  0.00, "N",
     "Parki narodowe - status ochronny"),

    ("ot_tcrz_a",  0.00, "N",
     "Rezerwaty - status ochronny"),

]


# ============================================================
# KONTROLA MACIERZY WAG
# ============================================================

def sprawdz_wagi():

    nazwy = [element[0] for element in WAGI_IVRF]
    wagi = [element[1] for element in WAGI_IVRF]

    if len(WAGI_IVRF) != 68:
        raise ValueError(
            f"Nieprawidlowa liczba wag: {len(WAGI_IVRF)}"
        )

    if len(set(nazwy)) != 68:
        raise ValueError(
            "Wykryto powtarzajace sie warstwy"
        )

    if any(waga < -1 or waga > 1 for waga in wagi):
        raise ValueError(
            "Waga poza zakresem -1 do 1"
        )

    for nazwa, waga, zrodlo, opis in WAGI_IVRF:

        if zrodlo not in ("Z", "P", "N"):
            raise ValueError(
                f"Bledne oznaczenie zrodla: {nazwa}"
            )

        if not opis:
            raise ValueError(
                f"Brak uzasadnienia: {nazwa}"
            )

        if (waga == 0) != (zrodlo == "N"):
            raise ValueError(
                f"Niezgodna waga neutralna: {nazwa}"
            )

    print("\nMACIERZ WAG IVRF - WERSJA 3")

    print(f"Liczba warstw: {len(WAGI_IVRF)}")
    print(f"Dodatnie: {sum(w > 0 for w in wagi)}")
    print(f"Ujemne: {sum(w < 0 for w in wagi)}")
    print(f"Neutralne: {sum(w == 0 for w in wagi)}")
    print("Kontrola macierzy: OK")


if __name__ == "__main__":
    sprawdz_wagi()
