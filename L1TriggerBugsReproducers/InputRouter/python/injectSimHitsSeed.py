import FWCore.ParameterSet.Config as cms
# from datetime import datetime

def injectSimHitsSeed(process):
    # Check for G4's simulated hits producer module
    if hasattr(process, 'g4SimHits'):
        # # Try a new seed
        # seed = int(datetime.now().timestamp())

        # This seed triggers a step 2 crash
        # runTheMatrix.py -w upgrade -l 30424 --nEvents 100 -t 16 -j 1 \
        #   --command "--customise Configuration/Geometry/injectSimHitsSeed.injectSimHitsSeed"
        seed = 1784726113

        print(f">>> injectSimHitsSeed: Injecting seed {seed}. " \
            f"Was: {process.RandomNumberGeneratorService.g4SimHits.initialSeed}")

        process.RandomNumberGeneratorService.g4SimHits.initialSeed = cms.untracked.uint32(seed)
    else:
        print(">>> injectSimHitsSeed: Skipping seed injection.")

    return process
