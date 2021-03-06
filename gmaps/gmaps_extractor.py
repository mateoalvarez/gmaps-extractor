"""
Script en desuso. Versión no optimizada.
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from multiprocessing.pool import Pool

from gmaps.places.extractor import PlacesExtractor
from gmaps.results.extractor import ResultsExtractor


def scrape_place(parameters):
    scraper = PlacesExtractor(driver_location=parameters.get("driver_location"),
                              url=parameters.get("url"),
                              place_name=parameters.get("place_name"),
                              num_reviews=parameters.get("num_reviews"),
                              output_config=parameters.get("output_config"),
                              postal_code=parameters.get("postal_code"),
                              extraction_date=parameters.get("extraction_date")
                              )
    scraped_info = scraper.scrap()
    return scraped_info


def export_data(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def get_parser():
    # driver_location: None, country: None, postal_code: None, places_types: None, num_pages: None)
    parser = argparse.ArgumentParser(
        prog='gmaps-scrapper',
        usage='gmaps-extractor.py -cp <postal_code> -d <driver_path> -c <country> -t <types_separated_by_colon> -p <pages>'
    )
    parser.add_argument('-cp', '--postal_code', nargs="?",
                        help='postal code', default="48005")
    parser.add_argument('-d', '--driver_path', nargs="?", help='selenium driver location',
                        default="/home/cflores/cflores_workspace/gmaps-extractor/resources/chromedriver")
    parser.add_argument('-c', '--country', nargs="?", help='country', default="Spain")
    parser.add_argument('-t', '--places_types', nargs='*', help='types of places separated by colon',
                        default=["Restaurants", "Bars"])
    parser.add_argument('-p', '--results_pages', nargs="?", help='number of pages to scrap', default=1, type=int)
    parser.add_argument('-n', '--num_reviews', nargs="?", help='number of reviews to scrap', default=3, type=int)
    parser.add_argument('-e', '--executors', nargs="?", help='number of executors', default=10, type=int)
    parser.add_argument('-m', '--output_mode', nargs="?", help='mode to store the output, local or remote',
                        default="remote", choices=["local", "remote"])
    parser.add_argument('-r', '--results_path', nargs="?", help='path where results would be located',
                        default="/home/cflores/cflores_workspace/gmaps-extractor/results", )
    parser.add_argument('-dc', '--db_config_path', nargs="?", help='remote db config file path',
                        default='/home/cflores/cflores_workspace/gmaps-extractor/resources/dbconfig.json')
    parser.add_argument('-l', '--debug_level', nargs=1, help='debug level', default="info",
                        choices=["debug", "info", "warning", "error", "critical"])
    return parser


def extract():
    parser = get_parser()
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout,
                        level=logging.getLevelName(args.debug_level.upper()),
                        datefmt="%d-%m-%Y %H:%M:%S",
                        format="[%(asctime)s] [%(levelname)8s] --- %(message)s (%(filename)s:%(lineno)d)")
    logger = logging.getLogger("gmaps_extractor")

    logger.info("arguments that will be used in the extraction are the following:")
    logger.info(args)
    db_config = None

    extraction_date = datetime.now().date().isoformat()
    if args.output_mode == "remote":
        if args.db_config_path:
            logger.info("output_mode set to {mode} and {config} file will be used to configure the remote connection"
                        .format(config=args.db_config_path, mode=args.output_mode))
            with open(args.db_config_path) as f:
                db_config = json.load(f)
        else:
            logger.info("{mode} is set but the argument db_config_path is not present. set db_config_path file (json)"
                        .format(mode=args.output_mode))
            parser.print_help()
            exit(-1)
    # else:
    #    extraction_date = extraction_date.strftime('%d-%m-%Y %H:%M:%S')
    data_file_name = "{country}_{cp}_{types}_{ts}.json".format(country=args.country.lower(),
                                                               cp=args.postal_code,
                                                               types="_".join([place_type.lower() for place_type in
                                                                               args.places_types]),
                                                               ts=int(time.time()))
    results_file_path = os.path.join(args.results_path, data_file_name)

    init_time = time.time()
    extractor = ResultsExtractor(driver_location=args.driver_path,
                                 country=args.country,
                                 postal_code=args.postal_code,
                                 places_types=args.places_types,
                                 num_pages=args.results_pages)
    places = extractor.scrap()
    logger.info("total of places found -{total}-".format(total=len(places)))
    # arguments list: [[#name #url #driver_location #num_reviews ]]
    # arguments_list = [[place, url, args.driver_path, args.num_reviews, db_config] for place, url in places.items()]
    #  driver_location: None, url: None, place_name: None, num_reviews: None, output_config: None,
    #                  postal_code: None, extraction_date: None
    arguments_list = [{"place_name": place,
                       "url": url,
                       "driver_location": args.driver_path,
                       "num_reviews": args.num_reviews,
                       "output_config": db_config,
                       "postal_code": args.postal_code,
                       "extraction_date": extraction_date
                       } for place, url in places.items()]

    data_results = []
    with Pool(processes=args.executors) as pool:
        data_results = pool.map(func=scrape_place, iterable=iter(arguments_list))
    if args.output_mode == "local":
        logger.info("storing locally the results")
        export_data(results_file_path, data_results)
        logger.info("results file can be found in: {file_path}".format(file_path=results_file_path))
    end_time = time.time()
    logger.info("total of spend time for extraction process: {total} seconds ".format(total=int(end_time - init_time)))


if __name__ == "__main__":
    extract()
