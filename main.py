from datetime import datetime, timedelta
import bs4
import cloudscraper
import shutil
import pandas as pd

scraper = cloudscraper.create_scraper(delay=10, browser="chrome")

columns = [
    "Title",
    "Categories",
    "Status",
    "Views",
    "Comments",
    "Follows",
    "Introduction",
    "Last Update",
    "Latest Chapter",
]
all_comics = pd.DataFrame(columns=columns)

def convert_last_update(last_update):
    last_update_components = last_update.split(' ')
    last_update_date = datetime.now()
    diff = timedelta(seconds=0)
    if len(last_update_components) == 3:
        if last_update_components[1] == 'giây':
            diff =timedelta(seconds=int(last_update_components[0]))
        elif last_update_components[1] == 'phút':
            diff =timedelta(minutes=int(last_update_components[0]))
        elif last_update_components[1] == 'giờ':
            diff =timedelta(hours=int(last_update_components[0]))
        elif last_update_components[1] == 'ngày':
            diff = timedelta(days=int(last_update_components[0]))
        last_update_date = last_update_date - diff
        return last_update_date.strftime('%d/%m/%Y')
    elif len(last_update_components) == 2:
        return f"{last_update_components[-1]}/{datetime.now().year}"
    return  f"{last_update_components[-1][:-2]}/20{last_update_components[-1][-1:]}"
   

def read_comic_data(comic) -> pd.Series:
    box_li = comic.select(".box_li")[0]
    title = box_li.select(".title")[0].text
    introduction = box_li.select(".box_text")[0].text
    detail_box = box_li.select(".message_main")[0].text
    # cover_url = box_li.select("img", attrs={'data-original':True})[0].get("data-original")[2:]
    
    details = detail_box.lstrip('\n').split('\n\n')
    detail_dict = {}

    for detail in details:
        try:
            key = detail.rstrip('\n').split(':')[0]
            value = ''.join(detail.rstrip('\n').split(':')[1:]) # case where name have ':'
            detail_dict[key]= value
        except Exception as e:
            print(detail)
            print(f"Error: {e}")
    last_update_date = convert_last_update(detail_dict['Ngày cập nhật'])
    

    latest_chapter = comic.select(".chapter.clearfix > a")[0].text
    return pd.Series(
        data=[title,
            detail_dict['Thể loại'],
            detail_dict['Tình trạng'],
            int(detail_dict['Lượt xem'].replace('.','')),
            int(detail_dict['Bình luận'].replace('.','')),
            int(detail_dict['Theo dõi'].replace('.','')),
            introduction,
            last_update_date,
            latest_chapter],
        index=columns,
    )


for page in range(90, 100):
    url: str = f"https://nettruyenco.com/?page={page}"
    response = scraper.get(url).text
    soup = bs4.BeautifulSoup(response, "html.parser")
    comics: list = soup.find("div", {"class": "items"}).select(".item")

    for comic in comics:
        comic_data = read_comic_data(comic)
        all_comics = all_comics.append(comic_data, ignore_index=True)

all_comics.to_csv('comics.csv')