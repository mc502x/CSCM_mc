"""French, Hindi and Georgian for the interface chrome (v4.3, added "just for fun").

Unlike the German catalogue (app/i18n_de.py, which the test suite holds complete) these three cover
the strings people see first - the top bar, the navigation, the login page, the dashboard and the
status code list - about a hundred each. Everything else falls back to the English text, so a page
is never blank, only partly translated. The translations are unreviewed: have a native speaker look
at them before they are shown to anybody who matters. tests/integration/test_roles_and_languages.py
checks that the three catalogues have the same keys and only translate strings that exist."""

from app.i18n_ar import AR  # noqa: E402  (Arabic lives in its own file)
from app.i18n_eu import CATALOGUES as EUROPEAN  # noqa: E402  (Spanish, Italian, Danish: v4.6)
from app.i18n_in import CATALOGUES as INDIAN  # noqa: E402  (so do the ten languages of v4.5)

# English text -> French / Hindi / Georgian. One tuple per string keeps the three in step.
_ROWS: list[tuple[str, str, str, str]] = [
    (
        "Skip to main content",
        "Aller au contenu principal",
        "मुख्य सामग्री पर जाएँ",
        "ძირითად შინაარსზე გადასვლა",
    ),
    ("Notices", "Notifications", "सूचनाएँ", "შეტყობინებები"),
    ("unread", "non lues", "अपठित", "წაუკითხავი"),
    ("Language", "Langue", "भाषा", "ენა"),
    (
        "You are covering for a colleague",
        "Vous remplacez un collègue",
        "आप एक सहकर्मी की जगह काम कर रहे हैं",
        "თქვენ კოლეგას ცვლით",
    ),
    ("covering", "remplacement", "प्रतिस्थापन", "ჩანაცვლება"),
    ("Account", "Compte", "खाता", "ანგარიში"),
    ("Log out", "Se déconnecter", "लॉग आउट", "გასვლა"),
    ("Main navigation", "Navigation principale", "मुख्य नेविगेशन", "მთავარი ნავიგაცია"),
    ("Dashboard", "Tableau de bord", "डैशबोर्ड", "მთავარი პანელი"),
    ("Status Codes", "Codes de statut", "स्थिति कोड", "სტატუსის კოდები"),
    ("New Status Code", "Nouveau code de statut", "नया स्थिति कोड", "ახალი სტატუსის კოდი"),
    ("New Sandbox Code", "Nouveau code de test", "नया सैंडबॉक्स कोड", "ახალი სატესტო კოდი"),
    ("Library Import", "Import de la bibliothèque", "लाइब्रेरी आयात", "ბიბლიოთეკის იმპორტი"),
    (
        "Import from .st files",
        "Importer depuis des fichiers .st",
        ".st फ़ाइलों से आयात करें",
        "იმპორტი .st ფაილებიდან",
    ),
    (
        "Legacy mapping",
        "Correspondance ancien-nouveau",
        "पुराने-नए की मैपिंग",
        "ძველი-ახალის შესაბამისობა",
    ),
    ("Workflow", "Flux de travail", "कार्यप्रवाह", "სამუშაო პროცესი"),
    (
        "My Change Requests",
        "Mes demandes de modification",
        "मेरे परिवर्तन अनुरोध",
        "ჩემი ცვლილების მოთხოვნები",
    ),
    ("Review Queue", "File de relecture", "समीक्षा कतार", "განხილვის რიგი"),
    ("Approval Queue", "File d'approbation", "अनुमोदन कतार", "დამტკიცების რიგი"),
    ("Change Sets", "Lots de modifications", "परिवर्तन समूह", "ცვლილებების ჯგუფები"),
    ("Stalled Requests", "Demandes en attente", "रुके हुए अनुरोध", "შეჩერებული მოთხოვნები"),
    ("Delegation", "Délégation", "प्रत्यायोजन", "დელეგირება"),
    ("Releases", "Versions publiées", "रिलीज़", "რელიზები"),
    ("Export Center", "Centre d'export", "निर्यात केंद्र", "ექსპორტის ცენტრი"),
    ("Insight", "Analyses", "विश्लेषण", "ანალიტიკა"),
    ("Catalogue Health", "Santé du catalogue", "कैटलॉग स्वास्थ्य", "კატალოგის მდგომარეობა"),
    ("Success Metrics", "Indicateurs de succès", "सफलता मापदंड", "წარმატების მაჩვენებლები"),
    ("Fleet Feedback", "Retour du parc", "बेड़े की प्रतिक्रिया", "პარკის უკუკავშირი"),
    ("Hub Consolidation", "Consolidation des Hub", "हब समेकन", "ჰაბის კონსოლიდაცია"),
    ("Administration", "Administration", "प्रशासन", "ადმინისტრირება"),
    ("Users", "Utilisateurs", "उपयोगकर्ता", "მომხმარებლები"),
    ("Lookups", "Listes de valeurs", "संदर्भ सूचियाँ", "საცნობარო სიები"),
    ("Export Profiles", "Profils d'export", "निर्यात प्रोफ़ाइल", "ექსპორტის პროფილები"),
    ("Review Checklist", "Liste de contrôle de relecture", "समीक्षा चेकलिस्ट", "განხილვის ჩეკლისტი"),
    ("Settings", "Paramètres", "सेटिंग्स", "პარამეტრები"),
    ("Integrations", "Intégrations", "एकीकरण", "ინტეგრაციები"),
    ("Operations", "Exploitation", "संचालन", "ოპერაციები"),
    ("Audit Log", "Journal d'audit", "ऑडिट लॉग", "აუდიტის ჟურნალი"),
    ("Help", "Aide", "सहायता", "დახმარება"),
    ("Log in", "Se connecter", "लॉग इन करें", "შესვლა"),
    (
        "Username or email",
        "Nom d'utilisateur ou e-mail",
        "उपयोगकर्ता नाम या ईमेल",
        "მომხმარებლის სახელი ან ელფოსტა",
    ),
    ("Password", "Mot de passe", "पासवर्ड", "პაროლი"),
    (
        "My Open Change Requests",
        "Mes demandes de modification ouvertes",
        "मेरे खुले परिवर्तन अनुरोध",
        "ჩემი ღია ცვლილების მოთხოვნები",
    ),
    (
        "Awaiting Cross-Domain Sign-Off",
        "En attente de validation inter-domaines",
        "क्रॉस-डोमेन स्वीकृति की प्रतीक्षा में",
        "ელოდება დომენთაშორის დადასტურებას",
    ),
    (
        "Awaiting Reviewer Sign-Off",
        "En attente de la validation du relecteur",
        "समीक्षक की स्वीकृति की प्रतीक्षा में",
        "ელოდება მიმომხილველის დადასტურებას",
    ),
    (
        "Awaiting Administrator Sign-Off",
        "En attente de la validation de l'administrateur",
        "प्रशासक की स्वीकृति की प्रतीक्षा में",
        "ელოდება ადმინისტრატორის დადასტურებას",
    ),
    (
        "Awaiting Chief Engineer Approval",
        "En attente de l'approbation de l'ingénieur en chef",
        "मुख्य अभियंता के अनुमोदन की प्रतीक्षा में",
        "ელოდება მთავარი ინჟინრის დამტკიცებას",
    ),
    ("Stalled requests", "Demandes en attente", "रुके हुए अनुरोध", "შეჩერებული მოთხოვნები"),
    ("overdue", "en retard", "विलंबित", "ვადაგადაცილებული"),
    (
        "Number ranges running out",
        "Plages de numéros bientôt épuisées",
        "समाप्त होती संख्या सीमाएँ",
        "ამოწურვადი ნომრების დიაპაზონები",
    ),
    (
        "Browse Status Codes",
        "Parcourir les codes de statut",
        "स्थिति कोड देखें",
        "სტატუსის კოდების დათვალიერება",
    ),
    (
        "Search and filter all governed status codes",
        "Rechercher et filtrer tous les codes de statut gouvernés",
        "सभी नियंत्रित स्थिति कोड खोजें और फ़िल्टर करें",
        "ყველა მართული სტატუსის კოდის ძიება და გაფილტვრა",
    ),
    (
        "Browse published and in-progress releases",
        "Parcourir les versions publiées et en cours",
        "प्रकाशित और जारी रिलीज़ देखें",
        "გამოქვეყნებული და მიმდინარე რელიზების დათვალიერება",
    ),
    (
        "Draft CRs of mine blocked on a domain sign-off",
        "Mes brouillons bloqués par une validation de domaine",
        "डोमेन स्वीकृति पर रुके मेरे ड्राफ़्ट अनुरोध",
        "დომენის დადასტურებაზე შეჩერებული ჩემი დრაფტები",
    ),
    (
        "New change set",
        "Nouveau lot de modifications",
        "नया परिवर्तन समूह",
        "ახალი ცვლილებების ჯგუფი",
    ),
    ("Change sets", "Lots de modifications", "परिवर्तन समूह", "ცვლილებების ჯგუფები"),
    ("Name", "Nom", "नाम", "სახელი"),
    (
        "Target software version",
        "Version logicielle cible",
        "लक्षित सॉफ़्टवेयर संस्करण",
        "სამიზნე პროგრამული ვერსია",
    ),
    ("Requests", "Demandes", "अनुरोध", "მოთხოვნები"),
    ("Status", "Statut", "स्थिति", "სტატუსი"),
    (
        "No change sets yet.",
        "Aucun lot de modifications pour l'instant.",
        "अभी कोई परिवर्तन समूह नहीं।",
        "ცვლილებების ჯგუფები ჯერ არ არის.",
    ),
    ("New Release", "Nouvelle version", "नई रिलीज़", "ახალი რელიზი"),
    ("Version", "Version", "संस्करण", "ვერსია"),
    ("Items", "Éléments", "आइटम", "ელემენტები"),
    ("Published", "Publié", "प्रकाशित", "გამოქვეყნებული"),
    (
        "No releases yet.",
        "Aucune version pour l'instant.",
        "अभी कोई रिलीज़ नहीं।",
        "რელიზები ჯერ არ არის.",
    ),
    (
        "Filter status codes",
        "Filtrer les codes de statut",
        "स्थिति कोड फ़िल्टर करें",
        "სტატუსის კოდების გაფილტვრა",
    ),
    ("Search", "Rechercher", "खोजें", "ძიება"),
    (
        "Identifier, title, description",
        "Identifiant, titre, description",
        "पहचानकर्ता, शीर्षक, विवरण",
        "იდენტიფიკატორი, სათაური, აღწერა",
    ),
    (
        "Functional System Group",
        "Groupe fonctionnel",
        "कार्यात्मक प्रणाली समूह",
        "ფუნქციური სისტემის ჯგუფი",
    ),
    ("any", "tous", "कोई भी", "ნებისმიერი"),
    ("Functional Subgroup", "Sous-groupe fonctionnel", "कार्यात्मक उप-समूह", "ფუნქციური ქვეჯგუფი"),
    ("Turbine Platform", "Plateforme d'éolienne", "टर्बाइन प्लेटफ़ॉर्म", "ტურბინის პლატფორმა"),
    ("Lifecycle", "Cycle de vie", "जीवनचक्र", "სასიცოცხლო ციკლი"),
    ("Status Category", "Catégorie de statut", "स्थिति श्रेणी", "სტატუსის კატეგორია"),
    ("Sandbox only", "Test uniquement", "केवल सैंडबॉक्स", "მხოლოდ სატესტო"),
    ("Filter", "Filtrer", "फ़िल्टर करें", "ფილტრი"),
    ("Columns", "Colonnes", "स्तंभ", "სვეტები"),
    ("Apply columns", "Appliquer les colonnes", "स्तंभ लागू करें", "სვეტების გამოყენება"),
    ("Link to this view", "Lien vers cette vue", "इस दृश्य का लिंक", "ბმული ამ ხედზე"),
    ("Saved searches", "Recherches enregistrées", "सहेजी गई खोजें", "შენახული ძიებები"),
    ("Remove", "Supprimer", "हटाएँ", "წაშლა"),
    (
        "No saved searches yet.",
        "Aucune recherche enregistrée.",
        "अभी कोई सहेजी गई खोज नहीं।",
        "შენახული ძიებები ჯერ არ არის.",
    ),
    (
        "Save the current filters as",
        "Enregistrer les filtres actuels sous",
        "वर्तमान फ़िल्टर इस नाम से सहेजें",
        "მიმდინარე ფილტრების შენახვა სახელით",
    ),
    ("Save search", "Enregistrer la recherche", "खोज सहेजें", "ძიების შენახვა"),
    ("Status codes", "Codes de statut", "स्थिति कोड", "სტატუსის კოდები"),
    ("Not yet assigned", "Pas encore attribué", "अभी निर्धारित नहीं", "ჯერ არ არის მინიჭებული"),
    ("Yes", "Oui", "हाँ", "დიახ"),
    ("No", "Non", "नहीं", "არა"),
    ("results", "résultats", "परिणाम", "შედეგი"),
    ("result", "résultat", "परिणाम", "შედეგი"),
    (
        "No status codes match these filters.",
        "Aucun code de statut ne correspond à ces filtres.",
        "इन फ़िल्टरों से कोई स्थिति कोड मेल नहीं खाता।",
        "ამ ფილტრებს არცერთი სტატუსის კოდი არ შეესაბამება.",
    ),
    ("Controller", "Contrôleur", "नियंत्रक", "კონტროლერი"),
    ("Number", "Numéro", "संख्या", "ნომერი"),
    ("level", "niveau", "स्तर", "დონე"),
    # the six roles (app/auth/roles.py) - a role badge shows these
    ("Administrator", "Administrateur", "प्रशासक", "ადმინისტრატორი"),
    ("StCd Owner", "Responsable StCd", "StCd स्वामी", "StCd-ის მფლობელი"),
    ("Chief Engineer", "Ingénieur en chef", "मुख्य अभियंता", "მთავარი ინჟინერი"),
    ("Reviewer", "Relecteur", "समीक्षक", "მიმომხილველი"),
    ("Engineer", "Ingénieur", "अभियंता", "ინჟინერი"),
    ("Viewer", "Lecteur", "दर्शक", "მაყურებელი"),
]

FR: dict[str, str] = {row[0]: row[1] for row in _ROWS}
HI: dict[str, str] = {row[0]: row[2] for row in _ROWS}
KA: dict[str, str] = {row[0]: row[3] for row in _ROWS}

CATALOGUES: dict[str, dict[str, str]] = {
    "fr": FR,
    "hi": HI,
    "ka": KA,
    "ar": AR,
    **INDIAN,
    **EUROPEAN,
}

from app.i18n_generated import merged  # noqa: E402

CATALOGUES = {code: merged(code, texts) for code, texts in CATALOGUES.items()}
