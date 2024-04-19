import os
import sys
import tempfile
import subprocess
from typing import NamedTuple, Any, List, Dict

import click
import requests
from datetime import datetime
import logging

# Logger
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel("INFO")

# Some constants
DEFAULT_URL = "https://cosmicweb.eu"
EDITOR = os.environ.get("EDITOR", "vim")


# Types
class Ellipsoid(NamedTuple):
    center: int
    shape: int
    traceback_radius: int
    radius_definition: int


class DownloadConfig(NamedTuple):
    simulation_name: str
    project_name: str
    halo_names: List[str]
    halo_ids: List[int]
    halo_urls: List[str]
    traceback_radius: float
    api_token: str
    MUSIC: Dict[str, str]
    settings: Dict[Any, Any]
    accessed_at: datetime


class Args(NamedTuple):
    url: str
    output_path: str
    common_directory: str
    attempts: int


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")


# Routines
def fetch_ellipsoids(url, api_token, attempts):
    for i in range(attempts):
        try:
            r = requests.get(url, headers={"Authorization": "Token " + api_token})
            # This will raise an error if not successful
            r.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logging.warning("Failed fetching (attempt {}/{}) ...".format(i, attempts))
            logging.warning(e)
        else:
            content = r.json()
            return [
                Ellipsoid(
                    center=e["ellips_center"],
                    shape=e["ellips_matrix"],
                    radius_definition=e["radius_definition"],
                    traceback_radius=e["traceback_radius"],
                )
                for e in content
            ]
    logging.error("Unable to download ellipsoids from {}".format(url))
    return None


def fetch_ellipsoid(url, api_token, traceback_radius, attempts=3):
    ellipsoids = fetch_ellipsoids(url, api_token, attempts)
    if ellipsoids is not None:
        return next(
            (e for e in ellipsoids if e.traceback_radius == traceback_radius), None
        )
    return None


def fetch_downloadstore(cosmicweb_url, target):
    try:
        r = requests.get(cosmicweb_url + "/api/music/store/" + target)
        # This will raise an error if not successful
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.critical(f"Failed downloading from cosmICweb.")
        logging.critical(e)
        sys.exit(1)
    content = r.json()
    sim = content["simulation"]
    halo_urls = [
        "{url}/simulation/{sid}/halo/{hid}".format(
            url=sim["api_url"], sid=sim["api_id"], hid=h
        )
        for h in content["halos"]
    ]
    return DownloadConfig(
        simulation_name=sim["name"],
        project_name=sim["project_name"],
        halo_names=["halo_{}".format(h) for h in content["halos"]],
        halo_ids=content["halos"],
        halo_urls=halo_urls,
        traceback_radius=content["traceback_radius"],
        api_token=sim["api_token"],
        MUSIC=sim["ics"],
        settings=content["configuration"],
        accessed_at=datetime.now(),
    )


def fetch_publication(cosmicweb_url, publication_name, traceback_radius):
    try:
        r = requests.get(cosmicweb_url + "/api/publications/" + publication_name)
        # This will raise an error if not successful
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.critical("Failed downloading from cosmICweb.")
        logging.critical(e)
        sys.exit(1)
    content = r.json()
    sim = content["simulation"]
    halo_names = [h["name"] for h in content["halos"]]
    halo_urls = [
        "{url}/simulation/{sid}/halo/{hid}".format(
            url=sim["api_url"], sid=sim["api_id"], hid=h["id"]
        )
        for h in content["halos"]
    ]
    return DownloadConfig(
        simulation_name=sim["name"],
        project_name=sim["project_name"],
        halo_names=halo_names,
        halo_ids=content["halos"],
        halo_urls=halo_urls,
        traceback_radius=traceback_radius,
        api_token=sim["api_token"],
        MUSIC=sim["ics"],
        settings={},
        accessed_at=datetime.now(),
    )


def edit_template(template):
    with tempfile.NamedTemporaryFile(suffix=".tmp", mode="r+") as tf:
        tf.write(template)
        tf.flush()
        # Call the editor. backupcopy=yes prevents vim from creating copy and rename
        subprocess.call([EDITOR, "+set backupcopy=yes", tf.name])
        tf.seek(0)
        template = tf.read()
    return template


def apply_config_parameter(config: str, parameters: dict[str, Any]):
    new_lines = []
    for line in config.split("\n"):
        param = line.split("=")[0].strip()
        if param in parameters:
            line = line.split("=")[0] + f"= {parameters[param]}"
        new_lines.append(line)
    return "\n".join(new_lines)


def music_config_to_template(config: DownloadConfig):
    music_config = config.MUSIC
    settings = config.settings
    # TODO: apply output configuration
    config = (
        f"# Zoom Initial Conditions for halo {config.halo_ids[0]} in simulation {config.simulation_name} ({config.project_name} project)\n"
        f"# Details on this halo can be found on https://cosmicweb.eu/simulation/{config.simulation_name}/halo/{config.halo_ids[0]}\n"
        f"# This file has been generated by CosmICweb @{datetime.now().isoformat()}\n\n\n"
        "[setup]\n" + music_config["setup"] + "\n\n<ELLIPSOID_TEMPLATE>\n\n"
        "[cosmology]\n" + music_config["cosmology"] + "\n\n"
        "[random]\n" + music_config["random"] + "\n\n"
        "[poisson]\n" + music_config["poisson"]
    )
    config = apply_config_parameter(
        config,
        {
            "levelmin": settings["resolution"]["low"],
            "levelmin_TF": settings["resolution"]["low"],
            "levelmax": settings["resolution"]["high"],
            "zstart": settings["startRedshift"],
        },
    )
    return config


def compose_template(template, ellipsoid):
    # TODO: add ellipsoid header (rtb, halo_name, etc)
    shape_0 = ", ".join(str(e) for e in ellipsoid.shape[0])
    shape_1 = ", ".join(str(e) for e in ellipsoid.shape[1])
    shape_2 = ", ".join(str(e) for e in ellipsoid.shape[2])
    center = ", ".join(str(x) for x in ellipsoid.center)

    ellipsoid_lines = (
        "# Ellipsoidal refinement region defined on unity cube\n"
        "# This minimum bounding ellipsoid has been obtained from\n"
        f"# particles within {ellipsoid.traceback_radius} {ellipsoid.radius_definition} of the halo center\n"
        "region = ellipsoid\n"
        f"region_ellipsoid_matrix[0] = {shape_0}\n"
        f"region_ellipsoid_matrix[1] = {shape_1}\n"
        f"region_ellipsoid_matrix[2] = {shape_2}\n"
        f"region_ellipsoid_center    = {center}\n"
    )
    return template.replace("<ELLIPSOID_TEMPLATE>", ellipsoid_lines)


def write_music_file(output_file, music_config):
    dirname = os.path.dirname(output_file)
    if not os.path.exists(dirname):
        logging.debug("Creating directory {}".format(dirname))
        os.makedirs(dirname)
    with open(output_file, "w") as f:
        f.write(music_config)


def call_music():
    pass


def process_config(config, args: Args):
    ellipsoids = []
    for halo_name, url in zip(config.halo_names, config.halo_urls):
        logging.info("Fetching ellipsoids from halo " + halo_name)
        ellipsoids.append(
            fetch_ellipsoid(
                url + "/ellipsoids",
                config.api_token,
                config.traceback_radius,
                args.attempts,
            )
        )

    # Edit template
    logging.info("Creating MUSIC template")
    music_template = music_config_to_template(config)

    if query_yes_no(
        "Do you want to edit the MUSIC template before creating the IC files?\n"
        "(changing zstart, levelmin, levelmax, etc.)",
        default="no",
    ):
        logging.debug("Editing MUSIC template")
        music_template = edit_template(music_template)
        logging.debug("Finished editing MUSIC template")
    # Store template to file
    for halo_name, ellipsoid in zip(config.halo_names, ellipsoids):
        if ellipsoid is None:
            logging.warning(
                "Ellipsoid for halo {} not available, skipping".format(halo_name)
            )
            continue
        logging.info("Composing MUSIC configuration file for halo {}".format(halo_name))
        music_config = compose_template(music_template, ellipsoid)
        if args.common_directory and len(ellipsoids) > 1:
            output_file = os.path.join(args.output_path, str(halo_name), "ics.cfg")
        else:
            output_file = os.path.join(args.output_path, "ics_{}.cfg".format(halo_name))
        logging.info(
            "Storing MUSIC configuration file for halo {} in {}".format(
                halo_name, output_file
            )
        )
        write_music_file(output_file, music_config)

    # TODO: Execute MUSIC?


def downloadstore_mode(args: Args, target: str):
    logging.info("Fetching download configuration from the cosmICweb server")
    config = fetch_downloadstore(args.url, target)
    if args.output_path == "./":
        args = args._replace(output_path=f"./cosmICweb-zooms-{config.simulation_name}")
        logging.debug("Output directory set to " + args.output_path)
    logging.info("Download configuration successfully fetched")
    process_config(config, args)


def publication_mode(args: Args, publication_name: str, traceback_radius: int):
    logging.info(
        "Fetching publication " + publication_name + " from the cosmICweb server"
    )
    config = fetch_publication(args.url, publication_name, traceback_radius)
    args = args._replace(output_path=os.path.join(args.output_path, publication_name))
    logging.debug("Output directory set to " + args.output_path)
    logging.info("Publication successfully fetched")
    process_config(config, args)


def dir_path(p):
    if os.path.isdir(p):
        return p
    else:
        raise NotADirectoryError(p)


@click.group()
@click.option(
    "--url", default=DEFAULT_URL, help="overwrite URL of the cosmICweb server"
)
@click.option(
    "--output-path",
    type=dir_path,
    default="./",
    help="Download target for IC files. If downloading publication, will create a subfolder with the name of the publication",
)
@click.option("--common-directory", is_flag=True)
@click.option(
    "--attempts", type=int, default=3, help="number of attempts to download ellipsoids"
)
@click.option("--verbose", is_flag=True)
@click.pass_context
def cli(ctx, url, output_path, common_directory, attempts, verbose):
    if verbose:
        logger.setLevel("DEBUG")
    ctx.obj = Args(
        url=url,
        output_path=output_path,
        common_directory=common_directory,
        attempts=attempts,
    )


@cli.command(help="Download ICs using a target UUID generated on cosmICweb")
@click.argument("target")
@click.pass_context
def get(ctx, target):
    args: Args = ctx.obj
    downloadstore_mode(args, target)


@cli.command(help="Download published ICs using the publication name")
@click.argument("publication_name")
@click.option("--traceback_radius", type=click.Choice([1, 2, 4, 10]), default=2)
@click.pass_context
def publication(ctx, publication_name, traceback_radius):
    args: Args = ctx.obj
    publication_mode(args, publication_name, traceback_radius)


if __name__ == "__main__":
    cli()

# if __name__ == "__main__":
#     parser = argparse.ArgumentParser()
#     parser.add_argument(
#         "--url",
#         dest="cosmicweb_url",
#         default=DEFAULT_URL,
#         help="overwrite URL of the cosmicweb server",
#     )
#     parser.add_argument(
#         "--output-path",
#         type=dir_path,
#         default="./",
#         help="Download target for IC files. If downloading publication, will create a subfolder with the "
#         "name of the publication",
#     )
#     parser.add_argument(
#         "--common-directory", dest="create_subdirs", action="store_false"
#     )
#     parser.add_argument(
#         "--attempts",
#         type=int,
#         default=3,
#         help="number of attempts to download ellipsoids",
#     )
#     parser.add_argument("--verbose", action="store_true")

#     subparsers = parser.add_subparsers(dest="mode")
#     # Downloading from publications
#     publication_parser = subparsers.add_parser(
#         "publication", help="download publications"
#     )
#     publication_parser.add_argument("publication_name", help="name of the publication")
#     publication_parser.add_argument(
#         "--traceback_radius", type=int, choices=[1, 2, 4, 10], default=2, help=""
#     )
#     # Downloading from download object
#     download_parser = subparsers.add_parser("get")
#     download_parser.add_argument("target")

#     args = parser.parse_args()

#     if args.verbose:
#         logger.setLevel("DEBUG")

#     if args.mode == "get":
#         downloadstore_mode(args)
#     elif args.mode == "publication":
#         publication_mode(args)
#     else:
#         raise NotImplementedError("unknown subparser")
