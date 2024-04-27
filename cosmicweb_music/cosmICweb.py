from __future__ import annotations

import os
import sys
import tempfile
import subprocess
from typing import Any
from .data_types import Ellipsoid, Args, DownloadConfig

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
EDITOR_IS_VIM = EDITOR in {"vim", "nvim"}


def query_yes_no(question: str, default="yes") -> bool:
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
def fetch_ellipsoids(url: str, api_token: str, attempts: int) -> list[Ellipsoid]:
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
    return []


def fetch_ellipsoid(
    url: str, api_token: str, traceback_radius: float, attempts: int = 3
) -> Ellipsoid | None:
    ellipsoids = fetch_ellipsoids(url, api_token, attempts)
    if ellipsoids:
        return next(
            (e for e in ellipsoids if e.traceback_radius == traceback_radius), None
        )
    return None


def fetch_downloadstore(cosmicweb_url: str, target: str) -> DownloadConfig:
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


def fetch_multiple(
    cosmicweb_url: str,
    traceback_radius,
    publication_name: str = None,
    collection_uuid: str = None,
) -> DownloadConfig:
    if publication_name:
        url = f"{cosmicweb_url}/api/publications/{publication_name}"
    elif collection_uuid:
        url = f"{cosmicweb_url}/api/collections/{collection_uuid}"
    else:
        raise ValueError("must provide either publication_name or collection_uuid")
    try:
        r = requests.get(url)
        # This will raise an error if not successful
        r.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.critical("Failed downloading from cosmICweb.")
        logging.critical(e)
        sys.exit(1)
    content = r.json()
    sim = content["simulation"]
    halo_names = []
    for h in content["halos"]:
        name = h["name"]
        if name is None:
            name = str(h["id"])
        halo_names.append(name)
    halo_ids = [h["id"] for h in content["halos"]]
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
        halo_ids=halo_ids,
        halo_urls=halo_urls,
        traceback_radius=traceback_radius,
        api_token=sim["api_token"],
        MUSIC=sim["ics"],
        settings=None,
        accessed_at=datetime.now(),
    )


def edit_template(template: str) -> str:
    with tempfile.NamedTemporaryFile(suffix=".tmp.conf", mode="r+") as tf:
        tf.write(template)
        tf.flush()
        editor_parameters = []
        if EDITOR_IS_VIM:
            # backupcopy=yes prevents vim from creating copy and rename
            editor_parameters.append("+set backupcopy=yes")
        subprocess.call([EDITOR] + editor_parameters + [tf.name])
        tf.seek(0)
        template = tf.read()
    return template


def apply_config_parameter(config: str, parameters: dict[str, Any]) -> str:
    new_lines = []
    for line in config.split("\n"):
        param = line.split("=")[0].strip()
        if param in parameters:
            line = line.split("=")[0] + f"= {parameters[param]}"
        new_lines.append(line)
    return "\n".join(new_lines)


def normalize_lineendings(text: str) -> str:
    return text.replace("\r\n", "\n")


def music_config_to_template(config: DownloadConfig) -> str:
    music_config = config.MUSIC
    music_config = {k: normalize_lineendings(v) for k, v in music_config.items()}

    settings = config.settings
    # TODO: apply output configuration
    config = (
        "[setup]\n" + music_config["setup"] + "\n\n<ELLIPSOID_TEMPLATE>\n\n"
        "[cosmology]\n" + music_config["cosmology"] + "\n\n"
        "[random]\n" + music_config["random"] + "\n\n"
        "[poisson]\n" + music_config["poisson"] + "\n\n"
    )
    if settings:
        config = apply_config_parameter(
            config,
            {
                "levelmin": settings["resolution"]["low"],
                "levelmin_TF": settings["resolution"]["low"],
                "levelmax": settings["resolution"]["high"],
                "zstart": settings["startRedshift"],
            },
        )
        if settings["outputType"]:
            config += f"""
[output]
format = {settings["outputType"]}
filename = {settings["outputFilename"]}
            """.strip()
            config += "\n"
            for k, v in settings["outputOptions"]:
                config += f"{k} = {v}\n"
    if not settings or not settings["outputType"]:
        # TODO: allow specifying output format via cli argument
        config += "[output]\n# TODO: add output options"
    return config


def compose_template(
    template: str,
    ellipsoid: Ellipsoid,
    config: DownloadConfig,
    halo_name: str,
    halo_id: int,
    now: datetime = None,
) -> str:
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
    template = template.replace("<ELLIPSOID_TEMPLATE>", ellipsoid_lines)
    if now is None:
        now = datetime.now()
    config_header = (
        f"# Zoom Initial Conditions for halo {halo_id} ({halo_name}) in simulation {config.simulation_name} ({config.project_name} project)\n"
        f"# Details on this halo can be found on https://cosmicweb.eu/simulation/{config.simulation_name}/halo/{halo_id}\n"
        f"# This file has been generated by CosmICweb @{now.isoformat()}\n\n\n"
    )
    return config_header + template + "\n"


def write_music_file(output_file: str, music_config: str) -> None:
    dirname = os.path.dirname(output_file)
    if not os.path.exists(dirname):
        logging.debug("Creating directory {}".format(dirname))
        os.makedirs(dirname)
    with open(output_file, "w") as f:
        f.write(music_config)


def call_music() -> None:
    pass


def process_config(config: DownloadConfig, args: Args, store: bool) -> None:
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
    output = []

    if store and query_yes_no(
        "Do you want to edit the MUSIC template before creating the IC files?\n"
        "(changing zstart, levelmin, levelmax, etc.)",
        default="no",
    ):
        logging.debug("Editing MUSIC template")
        music_template = edit_template(music_template)
        logging.debug("Finished editing MUSIC template")
    # Store template to file
    for halo_name, halo_id, ellipsoid in zip(
        config.halo_names, config.halo_ids, ellipsoids
    ):
        if ellipsoid is None:
            logging.warning(
                "Ellipsoid for halo {} not available, skipping".format(halo_name)
            )
            continue
        logging.info("Composing MUSIC configuration file for halo {}".format(halo_name))
        music_config = compose_template(
            music_template, ellipsoid, config, halo_name, halo_id
        )
        if args.common_directory and len(ellipsoids) > 1:
            output_file = os.path.join(args.output_path, str(halo_name), "ics.cfg")
        else:
            output_file = os.path.join(args.output_path, "ics_{}.cfg".format(halo_name))
        logging.info(
            "Storing MUSIC configuration file for halo {} in {}".format(
                halo_name, output_file
            )
        )
        if store:
            write_music_file(output_file, music_config)
        else:
            output.append((output_file, music_config))
    return output
    # TODO: Execute MUSIC?


def downloadstore_mode(args: Args, target: str, store=True) -> None | str:
    logging.info("Fetching download configuration from the cosmICweb server")
    config = fetch_downloadstore(args.url, target)
    if args.output_path == "./":
        args = args._replace(output_path=f"./cosmICweb-zooms-{config.simulation_name}")
        logging.debug("Output directory set to " + args.output_path)
    logging.info("Download configuration successfully fetched")
    return process_config(config, args, store)


def publication_mode(
    args: Args, publication_name: str, traceback_radius, store=True
) -> None | str:
    logging.info(f"Fetching publication {publication_name} from the cosmICweb server")
    config = fetch_multiple(
        args.url, traceback_radius, publication_name=publication_name
    )
    args = args._replace(output_path=os.path.join(args.output_path, publication_name))
    logging.debug("Output directory set to " + args.output_path)
    logging.info("Publication successfully fetched")
    return process_config(config, args, store)


def collection_mode(
    args: Args, collection_uuid: str, traceback_radius, store=True
) -> None | str:
    logging.info(f"Fetching collection {collection_uuid} from the cosmICweb server")
    config = fetch_multiple(args.url, traceback_radius, collection_uuid=collection_uuid)
    args = args._replace(
        output_path=os.path.join(args.output_path, config.simulation_name)
    )
    logging.debug("Output directory set to " + args.output_path)
    logging.info("Publication successfully fetched")
    print(config)
    return process_config(config, args, store)


def dir_path(p: str) -> str:
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
@click.option(
    "--common-directory",
    is_flag=True,
    help="store all config files in the same directory instead of individual directories for each halo",
)
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
@click.option(
    "--traceback_radius", type=click.Choice(["1", "2", "4", "10"]), default="2"
)
@click.pass_context
def publication(ctx, publication_name, traceback_radius):
    traceback_radius = float(traceback_radius)
    args: Args = ctx.obj
    publication_mode(args, publication_name, traceback_radius)


@cli.command(help="Download shared ICs using the collection UUID")
@click.argument("collection")
@click.option(
    "--traceback_radius", type=click.Choice(["1", "2", "4", "10"]), default="2"
)
@click.pass_context
def collection(ctx, collection, traceback_radius):
    traceback_radius = float(traceback_radius)
    args: Args = ctx.obj
    collection_mode(args, collection, traceback_radius)


if __name__ == "__main__":
    cli()
