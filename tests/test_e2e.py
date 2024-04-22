import re
from datetime import datetime

from cosmicweb_music.cosmICweb import (
    apply_config_parameter,
    music_config_to_template,
    process_config,
    DEFAULT_URL,
    compose_template,
    downloadstore_mode,
    publication_mode,
)
from cosmicweb_music.data_types import DownloadConfig, Args, Ellipsoid

reference_output = """
# Zoom Initial Conditions for halo 208416759 (halo_208416759) in simulation 150MPC (CosmOCA project)
# Details on this halo can be found on https://cosmicweb.eu/simulation/150MPC/halo/208416759
# This file has been generated by CosmICweb @2024-04-20T22:26:13.916577


[setup]
boxlength   = 150
zstart      = 99
levelmin    = 8
levelmin_TF = 8
levelmax    = 12
padding     = 16  # try reduce it at your own risk
overlap     = 4
align_top   = no
baryons     = no  # switch on for baryon runs
use_2LPT    = no
use_LLA     = no  # AMR codes might want to enable this

# Ellipsoidal refinement region defined on unity cube
# This minimum bounding ellipsoid has been obtained from
# particles within 10.0 Rvir of the halo center
region = ellipsoid
region_ellipsoid_matrix[0] = 872.2886068575001, -31.76815629375, 92.22811563824999
region_ellipsoid_matrix[1] = -31.76815629375, 520.6134379275, 28.34206946775
region_ellipsoid_matrix[2] = 92.22811563824999, 28.34206946775, 165.70762251300002
region_ellipsoid_center    = 0.42174551551333334, 0.42890526632, 0.27975938776000003


[cosmology]
Omega_m  = 0.309
Omega_L  = 0.691
Omega_b  = 0.049
H0       = 67.74
sigma_8  = 0.816
nspec    = 0.9667
transfer = eisenstein

[random]
cubesize = 256
seed[9]  = 74927
seed[10] = 21450

[poisson]
fft_fine      = true
accuracy      = 1e-5
grad_order    = 4
laplace_order = 4
""".lstrip()

reference_output_publication="""
# Zoom Initial Conditions for halo 25505622 (1e11v) in simulation AGORA (AGORA Project project)
# Details on this halo can be found on https://cosmicweb.eu/simulation/AGORA/halo/25505622
# This file has been generated by CosmICweb @2024-04-21T00:03:24.827918


[setup]
boxlength			= 60
zstart				= 100
levelmin			= 9
levelmin_TF			= 9
levelmax			= 9
padding				= 16  # try reduce it at your own risk
overlap				= 4
align_top			= no
baryons				= no  # switch on for baryon runs
use_2LPT			= no
use_LLA				= no  # AMR codes might want to enable this

# Ellipsoidal refinement region defined on unity cube
# This minimum bounding ellipsoid has been obtained from
# particles within 2.0 Rvir of the halo center
region = ellipsoid
region_ellipsoid_matrix[0] = 1202.685817644, -224.73030332520003, 78.4954201104
region_ellipsoid_matrix[1] = -224.73030332520003, 1126.675415484, -514.163771388
region_ellipsoid_matrix[2] = 78.4954201104, -514.163771388, 859.827522564
region_ellipsoid_center    = 0.6253459789833333, 0.47749109738333334, 0.6903304682000001


[cosmology]
Omega_m				= 0.272
Omega_L				= 0.728
Omega_b				= 0.0455
H0				= 70.2
sigma_8				= 0.807
nspec				= 0.961
transfer			= eisenstein
#below are MUSIC defaults to initialize gas temperature for some codes
#YHe				= 0.248     # primordial He abundance
#gamma				= 1.6667    # adiabatic exponent (=5/3)

[random]
cubesize			= 256
seed[8]				= 95064
seed[9]				= 31415
seed[10]			= 27183
# do not add higher seeds!

[poisson]
fft_fine		= yes
accuracy		= 1e-6
grad_order      	= 6
laplace_order   	= 6
""".lstrip()

time_fix_regex = re.compile(r"@[\d\-T:.]+")


def test_single_saved():
    id = "f5399734-ad67-432b-ba4d-61bc2088136a"
    args = Args(output_path="./", url=DEFAULT_URL, common_directory=True, attempts=1)
    output = downloadstore_mode(args, id, store=False)
    assert len(output) == 1
    output = output[0]
    assert output[0] == "./cosmICweb-zooms-150MPC/ics_halo_208416759.cfg"

    assert time_fix_regex.sub("TIME", output[1]) == time_fix_regex.sub(
        "TIME", reference_output
    )


def test_publication():
    id = "agora-halos"
    args = Args(output_path="./", url=DEFAULT_URL, common_directory=True, attempts=1)
    output = publication_mode(args, id, store=False, traceback_radius=2.0)
    assert len(output) == 6
    output = output[0]
    assert output[0] == "./agora-halos/1e11v/ics.cfg"

    assert time_fix_regex.sub("TIME", output[1]) == time_fix_regex.sub(
        "TIME", reference_output_publication
    )
