# AWS EC2 GPU Instance Specifications

## Generation 4 (G4dn / G4ad)

| Instance          | vCPUs | System Memory (GiB) | GPU       | Num of GPUs | GPU Memory (GB) | Hourly                 | Monthly             |
|:------------------|------:|--------------------:|:----------|------------:|----------------:|-----------------------:|--------------------:|
| **g4dn.xlarge**   |     4 |                  16 | NVIDIA T4 |           1 |              16 |                  $0.52 |                $383 |
| **g4dn.2xlarge**  |     8 |                  32 | NVIDIA T4 |           1 |              16 |                  $0.75 |                $548 |
| **g4dn.4xlarge**  |    16 |                  64 | NVIDIA T4 |           1 |              16 |                  $1.20 |                $878 |
| **g4dn.8xlarge**  |    32 |                 128 | NVIDIA T4 |           1 |              16 |                  $2.17 |              $1,588 |
| **g4dn.12xlarge** |    48 |                 192 | NVIDIA T4 |           4 |              64 |                  $3.91 |              $2,855 |
| **g4dn.16xlarge** |    64 |                 256 | NVIDIA T4 |           1 |              16 |                  $4.35 |              $3,176 |
| **g4dn.metal**    |    96 |                 384 | NVIDIA T4 |           8 |             128 |                  $7.82 |              $5,711 |

## Generation 5 (G5 / G5g)

| Instance         | vCPUs | CPU RAM (GB)  | GPU         | Num GPUs | GPU RAM (GB) | Hourly | Monthly |
|:-----------------|------:|--------------:|:------------|---------:|-------------:|-------:|--------:|
| **g5.xlarge**    |     4 |            16 | NVIDIA A10G |        1 |           24 |  $1.00 |    $734 |
| **g5.2xlarge**   |     8 |            32 | NVIDIA A10G |        1 |           24 |  $1.21 |    $884 |
| **g5.4xlarge**   |    16 |            64 | NVIDIA A10G |        1 |           24 |  $1.62 |  $1,185 |
| **g5.8xlarge**   |    32 |           128 | NVIDIA A10G |        1 |           24 |  $2.44 |  $1,787 |
| **g5.12xlarge**  |    48 |           192 | NVIDIA A10G |        4 |           96 |  $5.67 |  $4,140 |
| **g5.16xlarge**  |    64 |           256 | NVIDIA A10G |        1 |           24 |  $4.09 |  $2,990 |
| **g5.24xlarge**  |    96 |           384 | NVIDIA A10G |        4 |           96 |  $8.14 |  $5,945 |
| **g5.48xlarge**  |   192 |           768 | NVIDIA A10G |        8 |          192 | $16.28 | $11,890 |
|                  |       |               |             |          |              |        |         |
| **g5g.xlarge**   |     4 |             8 | NVIDIA T4g  |        1 |           16 |  $0.42 |    $306 |
| **g5g.2xlarge**  |     8 |            16 | NVIDIA T4g  |        1 |           16 |  $0.55 |    $405 |
| **g5g.4xlarge**  |    16 |            32 | NVIDIA T4g  |        1 |           16 |  $0.82 |    $604 |
| **g5g.8xlarge**  |    32 |            64 | NVIDIA T4g  |        1 |           16 |  $1.37 |  $1,001 |
| **g5g.16xlarge** |    64 |           128 | NVIDIA T4g  |        2 |           32 |  $2.74 |  $2,003 |
| **g5g.metal**    |    64 |           128 | NVIDIA T4g  |        2 |           32 |  $2.74 |  $2,003 |

## Generation 6 (G6 / G6e)

| Instance         | vCPUs | CPU RAM (GiB) | GPU         | Num GPUs | GPU RAM (GB) | Hourly | Monthly |
|:-----------------|------:|--------------:|:------------|---------:|-------------:|-------:|--------:|
| **g6.xlarge**    |     4 |            16 | NVIDIA L4   |        1 |           24 |  $0.80 |    $588 |
| **g6.2xlarge**   |     8 |            32 | NVIDIA L4   |        1 |           24 |  $0.98 |    $714 |
| **g6.4xlarge**   |    16 |            64 | NVIDIA L4   |        1 |           24 |  $1.32 |    $966 |
| **g6.8xlarge**   |    32 |           128 | NVIDIA L4   |        1 |           24 |  $2.01 |  $1,471 |
| **g6.12xlarge**  |    48 |           192 | NVIDIA L4   |        4 |           96 |  $4.60 |  $3,359 |
| **g6.16xlarge**  |    64 |           256 | NVIDIA L4   |        1 |           24 |  $3.40 |  $2,480 |
| **g6.24xlarge**  |    96 |           384 | NVIDIA L4   |        4 |           96 |  $6.68 |  $4,873 |
| **g6.48xlarge**  |   192 |           768 | NVIDIA L4   |        8 |          192 | $13.35 |  $9,746 |
|                  |       |               |             |          |              |        |         |
| **g6e.xlarge**   |     4 |            32 | NVIDIA L40S |        1 |           48 |  $1.86 |  $1,359 |
| **g6e.2xlarge**  |     8 |            64 | NVIDIA L40S |        1 |           48 |  $2.24 |  $1,637 |
| **g6e.4xlarge**  |    16 |           128 | NVIDIA L40S |        1 |           48 |  $3.00 |  $2,193 |
| **g6e.8xlarge**  |    32 |           256 | NVIDIA L40S |        1 |           48 |  $4.53 |  $3,306 |
| **g6e.12xlarge** |    48 |           384 | NVIDIA L40S |        4 |          192 | $10.49 |  $7,660 |
| **g6e.16xlarge** |    64 |           512 | NVIDIA L40S |        1 |           48 |  $7.58 |  $5,531 |
| **g6e.24xlarge** |    96 |           768 | NVIDIA L40S |        4 |          192 | $15.07 | $10,998 |
| **g6e.48xlarge** |   192 |          1536 | NVIDIA L40S |        8 |          384 | $30.13 | $21,996 |

## Generation 7 (G7e)

| Instance         | vCPUs | CPU RAM (GiB) | GPU                 | Num GPUs | GPU RAM (GB) | Hourly | Monthly |
|:-----------------|------:|--------------:|:--------------------|---------:|-------------:|-------:|--------:|
| **g7e.2xlarge**  |     8 |            64 | RTX PRO Server 6000 |        1 |           96 |  $3.36 |  $2,455 |
| **g7e.4xlarge**  |    16 |           128 | RTX PRO Server 6000 |        1 |           96 |  $3.99 |  $2,918 |
| **g7e.8xlarge**  |    32 |           256 | RTX PRO Server 6000 |        1 |           96 |  $5.26 |  $3,845 |
| **g7e.12xlarge** |    48 |           512 | RTX PRO Server 6000 |        2 |          192 |  $8.28 |  $6,048 |
| **g7e.24xlarge** |    96 |          1024 | RTX PRO Server 6000 |        4 |          384 | $16.57 | $12,097 |
| **g7e.48xlarge** |   192 |          2048 | RTX PRO Server 6000 |        8 |          768 | $33.14 | $24,195 |

## High Performance (P5 / P4 / P3)

| Instance          | vCPUs | CPU RAM (GiB) | GPU         | Num GPUs | GPU RAM (GB) | Hourly | Monthly |
|:------------------|------:|--------------:|:------------|---------:|-------------:|-------:|--------:|
| **p5.4xlarge**    |    16 |           256 | NVIDIA H100 |        1 |           80 |  $6.88 |  $5,022 |
| **p5.48xlarge**   |   192 |          2048 | NVIDIA H100 |        8 |           80 | $55.04 | $40,179 |
| **p5e.48xlarge**  |   192 |          2048 | NVIDIA H200 |        8 |          141 | $39.80 | $29,054 |
| **p5en.48xlarge** |   192 |          2048 | NVIDIA H200 |        8 |          141 | $63.30 | $46,209 |
|                   |       |               |             |          |              |        |         |
| **p4d.24xlarge**  |    96 |          1152 | NVIDIA A100 |        8 |           40 | $21.96 | $16,031 |
| **p4de.24xlarge** |    96 |          1152 | NVIDIA A100 |        8 |           80 | $27.45 | $20,039 |
|                   |       |               |             |          |              |        |         |
| **p3.2xlarge**    |     8 |            61 | NVIDIA V100 |        1 |           16 |  $3.06 |  $2,234 |
| **p3.8xlarge**    |    32 |           244 | NVIDIA V100 |        4 |           16 | $12.24 |  $8,935 |
| **p3.16xlarge**   |    64 |           488 | NVIDIA V100 |        8 |           16 | $24.48 | $17,870 |
| **p3dn.24xlarge** |    96 |           768 | NVIDIA V100 |        8 |           32 | $31.21 | $22,783 |

## The Blackwell Generation (P6)

| Instance           | vCPUs | System Memory (GiB) | GPU         | Number of GPUs | GPU Memory (GB) |
|:-------------------|------:|--------------------:|:------------|---------------:|----------------:|
| **p6-b200.48xlarge**|  192 |                2048 | NVIDIA B200 |              8 |             179 |
| **p6-b300.48xlarge**|  192 |                4096 | NVIDIA B300 |              8 |             269 |

## Price & Specs

| GPU          |  Price  | Year     | Bus Interface        | VRAM (GB) | Mem Type | Bandwidth (GB/s)           | Power (W)               |
|:-------------|--------:|:---------|:---------------------|----------:|:---------|:---------------------------|:------------------------|
| T4 16GB      |  $1,019 | Sep 2018 | PCIe Gen3 x16        |        16 | GDDR6    | 320                        | 75                      |
| A10G 24GB    |  $3,236 | Mar 2021 | PCIe Gen4 x16        |        24 | GDDR6    | 600                        | 150                     |
| L4 24GB      |  $4,720 | Mar 2023 | PCIe Gen4 x16        |        24 | GDDR6    | 300                        | 72                      |
| L40S 48GB    |  $8,904 | Aug 2023 | PCIe Gen4 x16        |        48 | GDDR6    | 864                        | 350                     |
| RTX 6000 PRO | $10,062 | Mar 2025 | PCIe 5.0 x16         |        96 | GDDR7    | 1,597                      | 600                     |
| V100 16GB    |    $724 | May 2017 | PCIe Gen3 x16        |        16 | HBM2     | 900                        | 250                     |
| A100 40GB    | $11,337 | May 2020 | PCIe Gen4 x16        |        40 | HBM2e    | 1,555                      | 250                     |
| A100 80GB    | $21,612 | May 2020 | PCIe Gen4 x16        |        80 | HBM2e    | 1,935                      | 300                     |
| H100 80GB    | $33,475 | Mar 2022 | PCIe Gen5 x16        |        80 | HBM3     | 2,000                      | 350                     |
| H200 141GB   | $38,356 | Nov 2023 | PCIe Gen5 x16        |       141 | HBM3e    | 4,800                      | 700                     |
