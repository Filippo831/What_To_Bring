from input_handler.input_handler import input_handler
import os

def main():
    '''
    iterate over the folders inside ./samples and create an array of samples with string inside that are:
    - folder name
    - path to personal_information.json
    - path to hike_information.json
    - path to course.gpx
    '''
    samples: list[dict[str, str]] = []
    for folder in os.listdir("./samples"):
        if os.path.isdir(os.path.join("./samples", folder)):
            sample = {
                "folder": folder,
                "personal_information": os.path.join("./samples", folder, "personal_information.json"),
                "hike_information": os.path.join("./samples", folder, "hike_information.json"),
                "course": os.path.join("./samples", folder, "course.gpx")
            }
            samples.append(sample)

    for sample in samples:
        input_handler(sample)

if __name__ == "__main__":
    main()
