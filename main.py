from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from cloudscraper import create_scraper
import shutil
import pandas as pd
import os


class Utility:
    @staticmethod
    def convert_last_update_to_date(last_update):
        last_update_components = last_update.split(" ")
        last_update_date = datetime.now()
        diff = timedelta(seconds=0)
        if len(last_update_components) == 3:
            if last_update_components[1] == "giây":
                diff = timedelta(seconds=int(last_update_components[0]))
            elif last_update_components[1] == "phút":
                diff = timedelta(minutes=int(last_update_components[0]))
            elif last_update_components[1] == "giờ":
                diff = timedelta(hours=int(last_update_components[0]))
            elif last_update_components[1] == "ngày":
                diff = timedelta(days=int(last_update_components[0]))
            last_update_date = last_update_date - diff
            return last_update_date.strftime("%d/%m/%Y")
        elif len(last_update_components) == 2:
            return f"{last_update_components[-1]}/{datetime.now().year}"
        return f"{last_update_components[-1][:-3]}/20{last_update_components[-1][-2:]}"

    @staticmethod
    def create_information_dictionary(raw_info):
        raw_info = raw_info.lstrip("\n").split("\n\n")
        information = {}
        for info in raw_info:
            try:
                key = info.rstrip("\n").split(":")[0]
                value = "".join(info.rstrip("\n").split(":")[1:])
                information[key] = value
            except Exception as e:
                print(f"Error: {e}")
        return information

    @staticmethod
    def to_comic(comic_card_soup):
        title = comic_card_soup.select(".title")[0].text
        introduction = comic_card_soup.select(".box_text")[0].text
        raw_info = comic_card_soup.select(".message_main")[0].text
        information = Utility.create_information_dictionary(raw_info)
        return Comic(
            title=title,
            author=information.get("Tác giả", "Unknown"),
            categories=information.get("Thể loại"),
            status=information.get("Tình trạng"),
            n_views=information.get("Lượt xem"),
            n_follows=information.get("Theo dõi"),
            n_comments=information.get("Bình luận"),
            last_update_date=Utility.convert_last_update_to_date(
                information.get("Ngày cập nhật")
            ),
            introduction=introduction,
        )


class Comic:
    def __init__(
        self,
        title,
        author,
        categories,
        status,
        n_views,
        n_follows,
        n_comments,
        last_update_date,
        introduction,
    ):
        self.title = title
        self.author = author
        self.categories = categories
        self.status = status
        self.n_views = n_views
        self.n_follows = n_follows
        self.n_comments = n_comments
        self.last_update_date = last_update_date
        self.introduction = introduction
        self.chapters = []

    def add_chapters(self, chapters):
        self.chapters.extend(chapters)

    def __str__(self):
        return f"""
        Title: {self.title}
        Author: {self.author}
        Categories: {self.categories}
        Status: {self.status}
        Views: {self.n_views} - Follows: {self.n_follows} - Comments: {self.n_comments}
        Last update date: {self.last_update_date}
        """


class ComicScraper:
    base_url = "http://www.nettruyenco.com/"

    def __init__(self, browser="chrome"):
        self.scraper = create_scraper(
            delay=10, browser={"browser": browser, "custom": "ScraperBot/2.0"}
        )
        self.comics = []

    def scrape_manga_list(self, from_page=1, to_page=1):
        all_comic_cards = []
        for page in range(from_page, to_page + 1):
            manga_list_url = f"{self.base_url}?page={page}"
            response = self.scraper.get(manga_list_url).content
            soup = BeautifulSoup(response, "html.parser")
            page_comic_cards = soup.find("div", {"class": "items"}).select(".item")
            all_comic_cards.extend(page_comic_cards)

        for comic_card in all_comic_cards:
            self.scrape_comic(comic_card)

    def scrape_comic(self, comic_card):
        comic = Utility.to_comic(comic_card)
        self.comics.append(comic)
        comic_cover_src = "https:" + (
            comic_card.find("img", {"data-original": True}).get("data-original")
        )
        comic_path = f"./comics/{comic.title}"
        if not os.path.exists(comic_path):
            os.makedirs(comic_path)
        with open(f"{comic_path}/cover.jpg", "wb") as cover_file:
            image_raw = self.scraper.get(comic_cover_src, stream=True).raw
            shutil.copyfileobj(image_raw, cover_file)
        with open(f"{comic_path}/info.txt", "w") as info_file:
            info_file.write(str(comic))

        comic_link = comic_card.select(".image > a")[0].get("href")
        self.scrape_chapters(comic_path, comic_link)

    def scrape_chapters(
        self, comic_path, comic_link, from_chapter=1, to_chapter=1
    ):  # return string contains chapter path
        soup = BeautifulSoup(self.scraper.get(comic_link).content, "html.parser")
        try:
            chapters = soup.select(".list-chapter")[0].select("li.row")[::-1][from_chapter:to_chapter+1]
            
            for chapter in chapters:
                chapter_name = chapter.select("a")[0].text
                chapter_path = f"{comic_path}/{chapter_name}"
                if not os.path.exists(chapter_path):
                    os.makedirs(chapter_path)
                chapter_url = chapter.select("a")[0].get("href")
                chapter_response = BeautifulSoup(
                    self.scraper.get(chapter_url).text, "html.parser"
                )
                pages = chapter_response.select(".page-chapter")
                self.scrape_pages(pages, chapter_path)
        except Exception as e:
            print(f"\nERROR: {e}")
            print(f"error path: {comic_link}")

    def scrape_pages(self, pages, chapter_path):
        for page in pages:
            page_url = "https:" + page.select("img")[0].get("data-original")
            page_image_raw = self.scraper.get(
                page_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Safari/537.36",
                    "Referer": "http://www.nettruyenco.com/",
                },
                stream=True,
            ).raw
            with open(f"{chapter_path}/{page.get('id')}.jpg", "wb") as out_file:
                shutil.copyfileobj(page_image_raw, out_file)


if __name__ == "__main__":
    comic_scraper = ComicScraper()
    comic_scraper.scrape_manga_list(from_page=1, to_page=1)
