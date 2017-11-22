# CONSTANTS: REPLACE WITH YOUR OWN INFO.  IN PARTICULAR, THE TWO DROPBOX FIELDS ARE TO GET YOUR API KEY OUT OF THE PYTHONISTA KEYCHAIN

DATABASE_FILENAME = "weight-tracker-TEST.db"
CSV_FILENAME = 'weights-TEST2.csv'

DROPBOX_KEYCHAIN_NAME = "keychain name goes here, see pythonista keychain docs-- e.g. 'dropbox'"
DROPBOX_KEYCHAIN_FIELD = "keychain field goes here-- e.g. 'myaccount'"

import dropbox, keychain, sqlite3, datetime, csv, dialogs
from matplotlib.pyplot import plot_date, show, subplots, legend
from matplotlib.dates import date2num, DateFormatter
from numpy import mean

token = keychain.get_password(DROPBOX_KEYCHAIN_NAME, DROPBOX_KEYCHAIN_FIELD)
dbx = dropbox.Dropbox(token)


def handle_api_error(e):
    errortype = e.error
    if errortype.is_path():
        if errortype.get_path().is_not_found():
            pass
        else:
            raise Exception("something went wrong on the dropbox end, panicking to save data.")
    else:
        raise Exception("something went wrong on the dropbox end, panicking to save data.")

def get_db_file():
    path = "/" + DATABASE_FILENAME
    try:
        dbx.files_download_to_file(DATABASE_FILENAME, path)
    except dropbox.exceptions.ApiError as e:
        handle_api_error(e)

def upload_database():
    with open(DATABASE_FILENAME, 'rb') as f:
        data = f.read()
    path = '/' + DATABASE_FILENAME
    dbx.files_upload(data, path, dropbox.files.WriteMode.overwrite)

def connect_to_db():  # being consciously inefficient here, going to attempt to create table every time since perf is meaningless
    get_db_file()  # make sure that if there's a database on the dropbox we get that.
    conn = sqlite3.connect(DATABASE_FILENAME, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    # see https://stackoverflow.com/questions/1829872/how-to-read-datetime-back-from-sqlite-as-a-datetime-instead-of-string-in-python
    table = """ CREATE TABLE IF NOT EXISTS weights (
                                        id integer PRIMARY KEY,
                                        date timestamp NOT NULL,
                                        weight integer NOT NULL
                                    ); """
    # weights will be stored as integers by multiplying original weight by 10 in order to eliminate floating point error.  The only time there will be a floating point representation is when printing.
    c = conn.cursor()
    c.execute(table)
    return conn

def add_weight(weight):
    conn = connect_to_db()
    insert_weight = "INSERT INTO weights(date,weight) VALUES(?,?)"
    c = conn.cursor()
    data = (datetime.datetime.now(), weight)
    c.execute(insert_weight, data)
    conn.commit()
    conn.close()
    upload_database()
    print("added!")

def get_csv():
    conn = connect_to_db()
    c = conn.cursor()
    c.execute("SELECT * FROM weights")
    data = c.fetchall()
    conn.close()
    with open(CSV_FILENAME, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'date', 'weight'])
        writer.writerows(data)

def validate_input(weight):
    bits = weight.partition(".")
    characteristic = bits[0].isdigit()
    point = bits[1] == "."
    mantissa = bits[2].isdigit()
    rightsize = len(bits[2]) == 1
    return characteristic and point and mantissa and rightsize
    

def parse_input(weight):
    if validate_input(weight):
        try:
            num = int(weight.replace(".", ""))
        except:
            raise ValueError("enter a number with exactly one decimal place.")
        return(num)
    else:
        raise ValueError("enter a number with exactly one decimal place.")

def moving_average(size, indata):
    outdata = []
    for idx, item in enumerate(indata):
        endpoint = idx + 1
        if idx < size:
            field = indata[0:endpoint]
        else:
            field = indata[endpoint - size: endpoint]
        outdata.append(mean(field) / 10)
    return outdata
        

def get_plotting_data():
    conn = connect_to_db()
    c = conn.cursor()
    c.execute("SELECT * FROM weights")
    data = c.fetchall()
    dates = date2num([x[1] for x in data])
    raw_weights = [x[2]  / 10.0 for x in data]
    smoothed_5 = moving_average(5, [x[2] for x in data])
    smoothed_10 = moving_average(10, [x[2] for x in data])
    return {"dates": dates, "smoothed_5": smoothed_5, "smoothed_10": smoothed_10, "raw_weights": raw_weights}

def plot_db():
    data = get_plotting_data()
    myFmt = DateFormatter('%-m-%d')
    fig, ax = subplots()
    ax.xaxis.set_major_formatter(myFmt)
    plot_date(data["dates"], data["smoothed_5"], fmt="b-", label="5-day average")
    plot_date(data["dates"], data["smoothed_10"], fmt="g-", label="10-day average")
    plot_date(data["dates"], data["raw_weights"], fmt="r-", label="daily weights")
    legend(loc='upper left')
    show()        

if __name__ == "__main__":
    user_input = dialogs.form_dialog(fields=[{"type": "text", "key": "weight", "title": "Weight:", "placeholder": "ONE DECIMAL PLACE EXACTLY (example: 100.0)"}])
    if user_input["weight"]:
        add_weight(parse_input(user_input["weight"]))
        print("added weight.  now saving updated csv.")
    else:
        print("no data to add.  downloading db and saving csv.")
    get_csv()
    plot_db()

