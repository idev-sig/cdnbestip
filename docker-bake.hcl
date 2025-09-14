## https://docs.docker.com/build/bake/
## https://docs.docker.com/reference/cli/docker/buildx/bake/#set
## https://github.com/crazy-max/buildx#remote-with-local
## https://github.com/docker/metadata-action

## Special target: https://github.com/docker/metadata-action#bake-definition
target "docker-metadata-action" {}

variable "DEFAULT_IMAGE" {
    default = "idevsig/cdnbestip"
}

target "_image" {
    inherits = ["docker-metadata-action"]
}

target "_common" {
    labels = {
        "org.opencontainers.image.authors" = "Jetsung Chan<i@jetsung.com>"
    }
    context = "."
    dockerfile = "docker/Dockerfile"
    args = {
    }
    platforms = ["linux/amd64"]
}

target "default" {
    inherits = ["_common"]
    args = {
    }
    tags = [
      "${DEFAULT_IMAGE}:local",
    ]
}

group "dev" {
  targets = ["dev"]
}

target "dev" {
    inherits = ["_common", "_image"]
}

group "release" {
  targets = ["release"]
}

target "release" {
    inherits = ["_common", "_image"]
    platforms = ["linux/amd64","linux/arm64"]
}
