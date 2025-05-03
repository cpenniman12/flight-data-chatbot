# Set CRAN mirror
options(repos = c(CRAN = "https://cloud.r-project.org"))

# Install and load necessary packages
if (!require("nycflights13")) {
  install.packages("nycflights13")
}
if (!require("tidyverse")) {
  install.packages("tidyverse")
}

library(nycflights13)
library(tidyverse)

# Create output directory if it doesn't exist
output_dir <- "nycflights_data"
if (!dir.exists(output_dir)) {
  dir.create(output_dir)
}

# Export the datasets to CSV files
write_csv(airlines, file.path(output_dir, "airlines.csv"))
write_csv(airports, file.path(output_dir, "airports.csv"))
write_csv(planes, file.path(output_dir, "planes.csv"))
write_csv(weather, file.path(output_dir, "weather.csv"))
write_csv(flights, file.path(output_dir, "flights.csv"))

cat("Exported all nycflights13 datasets to", output_dir, "directory\n") 