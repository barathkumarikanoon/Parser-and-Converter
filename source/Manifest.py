# import json
# import logging
# import os
# from pathlib import Path
# from iiif_prezi.factory import ManifestFactory
# from PIL import Image


# class IIIFManifest:

#     def __init__(self, output_dir, label, base_prez_uri = None):
#         self.logger = logging.getLogger(__name__)
#         self.output_dir = Path(output_dir)
#         self.label = label
#         self.base_prez_uri = self._resolve_base_uri(base_prez_uri)

#         self.manifest_dir = self.output_dir / 'manifest' / label
#         self.manifest_path = self.manifest_dir / 'manifest.json'

#     def _resolve_base_uri(self, base_prez_uri):
#         if base_prez_uri:
#             return base_prez_uri.rstrip('/')

#         host = os.environ.get('HOST', 'localhost')
#         port = os.environ.get('PORT', '8000')
#         scheme = os.environ.get('SCHEME', 'http')
#         return '%s://%s:%s' % (scheme, host, port)

#     def ensure_dirs(self):
#         self.manifest_dir.mkdir(parents=True, exist_ok=True)

#     def build_uri(self, path):
#         path = Path(path)
#         try:
#             relative_path = path.relative_to(self.output_dir)
#             return self.base_prez_uri + '/' + relative_path.as_posix()
#         except ValueError:
#             return self.base_prez_uri + '/' + path.as_posix().lstrip('/')

#     def get_image_info(self, img_path):
#         img_path = Path(img_path)
#         with Image.open(img_path) as img:
#             width, height = img.size
#             suffix = img_path.suffix.lower()
#             if suffix == '.png':
#                 image_format = 'image/png'
#             elif suffix in ('.jpg', '.jpeg'):
#                 image_format = 'image/jpeg'
#             else:
#                 image_format = 'image/' + suffix.lstrip('.')

#         return width, height, image_format


#     def generate_iiif(self, images, metadata=None):
#         self.ensure_dirs()

#         # Configure ManifestFactory
#         manifest_factory = ManifestFactory()
#         manifest_factory.set_base_prezi_dir(str(self.manifest_path.parent))
#         manifest_factory.set_base_prezi_uri(self.base_prez_uri)
#         # manifest_factory.set_base_image_uri(self.base_image_uri)

#         # Create manifest
#         manifest = manifest_factory.manifest(
#             ident=f"manifest/{self.label}/manifest.json",
#             label=f"IIIF Manifest: {self.label}"
#         )

#         manifest.description = f"IIIF Manifest with images for {self.label}"

#         if metadata:
#             manifest.set_metadata(metadata)

#         # Create sequence
#         sequence = manifest.sequence()

#         for idx, img in enumerate(images):
#             try:
#                 img_path = Path(img)

#                 if not img_path.exists():
#                     self.logger.warning("Image does not exist: %s", img_path)
#                     continue

#                 image_uri = self.build_uri(img_path)

#                 # Canvas
#                 canvas = sequence.canvas(
#                     ident=f"manifest/{self.label}/canvas/{idx}",
#                     label=f"Canvas {idx + 1}"
#                 )

#                 # Annotation
#                 annotation = canvas.annotation(
#                     ident=f"manifest/{self.label}/annotation/{idx}"
#                 )

#                 # Regular image (NOT IIIF Image API)
#                 ann_image = annotation.image(image_uri)

#                 # Populate width & height
#                 ann_image.set_hw_from_file(str(img_path))
#                 canvas.width = ann_image.width
#                 canvas.height = ann_image.height

#             except Exception as e:
#                 self.logger.warning("Skipping image %s: %s", img, e)

#         # Write manifest.json
#         manifest.toFile(compact=False)

#     def create_from_images(self, images, metadata = None):
#         try:
#             self.ensure_dirs()
#             self.generate_iiif(images, metadata)
#             return self.manifest_path
#         except Exception as e:
#             self.logger.warning('While generating IIIF Manifest for %s: %s', self.label, e)
#             return None

import logging
import os
from pathlib import Path

from iiif_prezi.factory import ManifestFactory


class IIIFManifest:

    def __init__(self, output_dir, label, base_prez_uri=None):
        self.logger = logging.getLogger(__name__)

        self.output_dir = Path(output_dir).resolve()
        self.label = label

        self.manifest_dir = self.output_dir / "manifest" / label
        self.manifest_path = self.manifest_dir / "manifest.json"

        self.base_prez_uri = self._resolve_base_uri(base_prez_uri)

    def _resolve_base_uri(self, base_prez_uri=None):
        """
        Public URI corresponding to output_dir.

        Production:
            https://gazettes.servantsofknowledge.in/gzdl/html/andhra/2018-03-01

        Development:
            http://localhost:8000
        """

        if base_prez_uri:
            return base_prez_uri.rstrip("/")

        return os.environ.get(
            "PUBLIC_BASE_URL",
            "http://localhost:8000"
        ).rstrip("/")

    def ensure_dirs(self):
        self.manifest_dir.mkdir(parents=True, exist_ok=True)

    def build_uri(self, image_path):
        """
        Convert an image path under output_dir into a public URI.
        """

        image_path = Path(image_path).resolve()

        rel = image_path.relative_to(self.output_dir)

        return f"{self.base_prez_uri}/{rel.as_posix()}"

    def generate_iiif(self, images, metadata=None):

        self.ensure_dirs()

        factory = ManifestFactory()

        #
        # Root of generated files
        #
        factory.set_base_prezi_dir(str(self.output_dir))

        #
        # Root public URL
        #
        factory.set_base_prezi_uri(self.base_prez_uri)

        manifest = factory.manifest(
            ident=f"manifest/{self.label}/manifest.json",
            label=f"IIIF Manifest: {self.label}"
        )

        manifest.description = (
            f"IIIF Manifest with images for {self.label}"
        )

        manifest.viewingHint = "paged"
        manifest.viewingDirection = "left-to-right"

        if metadata:
            manifest.set_metadata(metadata)

        sequence = manifest.sequence()

        for idx, image in enumerate(images):

            try:

                image_path = Path(image).resolve()

                if not image_path.exists():
                    self.logger.warning(
                        "Image not found: %s",
                        image_path
                    )
                    continue

                canvas = sequence.canvas(
                    ident=f"manifest/{self.label}/canvas-{idx}.json",
                    label=f"Canvas {idx + 1}"
                )

                annotation = canvas.annotation(
                    ident=f"manifest/{self.label}/annotation-{idx}.json"
                )

                ann_image = annotation.image(
                    self.build_uri(image_path)
                )

                ann_image.set_hw_from_file(str(image_path))

                ann_image.format = self.get_image_format(image_path)

                canvas.width = ann_image.width
                canvas.height = ann_image.height

            except Exception:
                self.logger.exception(
                    "Failed processing image %s",
                    image
                )

        manifest.toFile(compact=False)

    
    def get_image_format(self, image_path):
        suffix = Path(image_path).suffix.lower()

        if suffix == ".png":
            return "image/png"

        if suffix in (".jpg", ".jpeg"):
            return "image/jpeg"

        if suffix == ".tif":
            return "image/tiff"

        if suffix == ".tiff":
            return "image/tiff"

        return f"image/{suffix.lstrip('.')}"

    def create_from_images(self, images, metadata=None):

        try:
            self.generate_iiif(images, metadata)
            return self.manifest_path

        except Exception:
            self.logger.exception(
                "Failed generating IIIF manifest for %s",
                self.label
            )
            return None