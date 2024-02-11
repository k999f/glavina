import json
import copy
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from shapely.geometry import Point, LineString
from shapely.geometry.polygon import Polygon
from shapely.ops import unary_union
import networkx as nx
import time


def read_obstacles_data(polygons, obstacles_path):
    with open(obstacles_path, "r") as j:
        obstacles_data = json.loads(j.read())

    for obstacle in obstacles_data:
        if obstacle["type"] == "polygon":
            point_coordinates = dict()
            polygons_coordinates = list()
            for point in obstacle["points"]:
                point_coordinates["x"] = round(point["x"], 3)
                point_coordinates["y"] = round(point["y"], 3)
                polygons_coordinates.append(copy.deepcopy(point_coordinates))
                point_coordinates.clear()
            polygons.append(polygons_coordinates)


def create_polygons(polygons_data):
    polygons_coordinates = list()
    polygons = list()

    for polygon in polygons_data:
        coordinates = list()
        for points in polygon:
            coordinates.append((points["x"], points["y"]))
        polygons_coordinates.append(coordinates)

    for coordinates in polygons_coordinates:
        polygons.append(Polygon(coordinates))

    return polygons


def show_obstacles(polygons):
    for polygon in polygons:
        plt.figure(0)
        plt.plot(*polygon.exterior.xy, color="grey", linewidth=0.7)

    plt.xlim([0, plot_size])
    plt.ylim([0, plot_size])


def show_path(start_x, start_y, end_x, end_y, path, color):
    path_xs = list()
    path_ys = list()

    i = 0
    for point in path:
        if i == 0:
            path_xs.append(point["x"])
            path_ys.append(point["y"])
            previous_point = point
        else:
            path_xs.append(previous_point["x"])
            path_xs.append(point["x"])
            path_ys.append(previous_point["y"])
            path_ys.append(point["y"])
            previous_point = point
        i += 1

    plt.figure(0)
    if color == "black":
        plt.plot(path_xs, path_ys, linestyle="dashed",
                 color="black", linewidth=0.5)
    elif color == "red":
        plt.plot(path_xs, path_ys, linestyle="dashed",
                 color="red", linewidth=0.5)


def gds(polygons, start_x, start_y, end_x, end_y):
    path = list()
    i = 0
    x = start_x
    y = start_y
    while x != end_x and y != end_y:
        line = LineString([(x, y), (end_x, end_y)])
        new_point = line.interpolate(step)

        i += 1
        for polygon in polygons:
            if new_point.within(polygon):
                intersections = line.intersection(polygon)
                if intersections.geom_type == "LineString":
                    intersection = list(line.intersection(polygon).coords)
                else:
                    lines = list(line.intersection(polygon).geoms)
                    intersection = list(lines[0].coords)
                new_point = Point(intersection[0][0], intersection[0][1])
                new_line = LineString(
                    [(new_point.x, new_point.y), (end_x, end_y)])
                left_line = new_line.offset_curve(step)
                right_line = new_line.offset_curve(-step)
                left_point = Point(left_line.coords[0])
                right_point = Point(right_line.coords[0])
                if (
                    not left_point.within(polygon)
                    and (0 <= left_point.x <= plot_size)
                    and (0 <= left_point.y <= plot_size)
                ):
                    new_point = left_point
                elif (
                    not right_point.within(polygon)
                    and (0 <= right_point.x <= plot_size)
                    and (0 <= right_point.y <= plot_size)
                ):
                    new_point = right_point
                else:
                    return path, True, "can't move", (x, y)
                break

        x = new_point.x
        y = new_point.y
        if print_points:
            if i % (max_iterations / 40) == 0:
                print("iteration: " + str(i) +
                      ", point: " + str(x) + "; " + str(y))
        path.append({"x": x, "y": y})

        if i == max_iterations:
            return path, True, "out of iterations", (x, y)

    return path, False, None, None


def create_subgoal(polygons):
    i = 0
    random_x = round(random.uniform(0, plot_size), 3)
    random_y = round(random.uniform(0, plot_size), 3)
    while i < len(polygons):
        if Point(random_x, random_y).within(polygons[i]):
            random_x = round(random.uniform(0, plot_size), 2)
            random_y = round(random.uniform(0, plot_size), 2)
            i = 0
        else:
            i += 1
    return (random_x, random_y)


def gds_subgoal(polygons, start_x, start_y, end_x, end_y):
    global subgoals_count
    global max_subgoals_reached
    if subgoals_count == max_subgoals:
        max_subgoals_reached = True
        return
    subgoal = create_subgoal(polygons)
    subgoals_count += 1
    subgoals.append(subgoal)
    subgoal_number = subgoals_count
    print(
        "Random subgoal "
        + str(subgoals_count)
        + " created at: "
        + str(round(subgoal[0], 3))
        + "; "
        + str(round(subgoal[1], 3))
    )

    plt.figure(0)
    plt.plot(subgoal[0], subgoal[1], marker="o", color="blue", markersize=4)
    if show_subgoals_numbers:
        plt.text(
            subgoal[0], subgoal[1], str(subgoals_count), color="black", fontsize=11
        )

    start_subgoal_path, start_subgoal_stuck, stuck_reason, stuck_point = gds(
        polygons, start_x, start_y, subgoal[0], subgoal[1]
    )
    if start_subgoal_stuck:
        print(
            "Subgoal "
            + str(subgoal_number)
            + " -> start: failed ("
            + stuck_reason
            + ")"
        )
        if subgoals_count < max_subgoals:
            subgoals_count += 1
            subgoals.append(stuck_point)
            print(
                "Subgoal "
                + str(subgoals_count)
                + " created at: "
                + str(round(stuck_point[0], 3))
                + "; "
                + str(round(stuck_point[1], 3))
            )
            graph.add_edge("s", subgoals_count, path=start_subgoal_path)

            plt.figure(0)
            show_path(
                start_x,
                start_y,
                stuck_point[0],
                stuck_point[1],
                start_subgoal_path,
                "black",
            )
            plt.plot(
                stuck_point[0], stuck_point[1], marker="o", color="blue", markersize=4
            )
            if show_subgoals_numbers:
                plt.text(
                    stuck_point[0],
                    stuck_point[1],
                    str(subgoals_count),
                    color="black",
                    fontsize=11,
                )
        else:
            print("Can't create subgoal (maximum reached)")

    else:
        print("Subgoal " + str(subgoal_number) + " -> start: success")
        graph.add_edge("s", subgoal_number, path=start_subgoal_path)
        show_path(start_x, start_y, subgoal[0],
                  subgoal[1], start_subgoal_path, "black")
        if nx.has_path(graph, "s", "e"):
            return

    subgoal_end_path, subgoal_end_stuck, stuck_reason, stuck_point = gds(
        polygons, subgoal[0], subgoal[1], end_x, end_y
    )
    if subgoal_end_stuck:
        print(
            "Subgoal " + str(subgoal_number) +
            " -> end: failed (" + stuck_reason + ")"
        )
        if subgoals_count < max_subgoals:
            subgoals_count += 1
            subgoals.append(stuck_point)
            print(
                "Subgoal "
                + str(subgoals_count)
                + " created at: "
                + str(round(stuck_point[0], 3))
                + "; "
                + str(round(stuck_point[1], 3))
            )
            graph.add_edge(subgoal_number, subgoals_count,
                           path=subgoal_end_path)

            plt.figure(0)
            show_path(
                subgoal[0],
                subgoal[1],
                stuck_point[0],
                stuck_point[1],
                subgoal_end_path,
                "black",
            )
            plt.plot(
                stuck_point[0], stuck_point[1], marker="o", color="blue", markersize=4
            )
            if show_subgoals_numbers:
                plt.text(
                    stuck_point[0],
                    stuck_point[1],
                    str(subgoals_count),
                    color="black",
                    fontsize=11,
                )
        else:
            print("Can't create subgoal (maximum reached)")

    else:
        print("Subgoal " + str(subgoal_number) + " -> end: success")
        graph.add_edge(subgoal_number, "e", path=subgoal_end_path)
        show_path(subgoal[0], subgoal[1], end_x,
                  end_y, subgoal_end_path, "black")
        if nx.has_path(graph, "s", "e"):
            return

    for i in range(len(subgoals)):
        if i == subgoal_number:
            continue
        subgoal_subgoal_path, subgoal_subgoal_stuck, stuck_reason, stuck_point = gds(
            polygons, subgoal[0], subgoal[1], subgoals[i][0], subgoals[i][1]
        )
        if subgoal_subgoal_stuck:
            print(
                "Subgoal "
                + str(subgoal_number)
                + " -> subgoal "
                + str(i)
                + ": failed ("
                + stuck_reason
                + ")"
            )
            if subgoals_count < max_subgoals:
                subgoals_count += 1
                subgoals.append(stuck_point)
                print(
                    "Subgoal "
                    + str(subgoals_count)
                    + " created at: "
                    + str(round(stuck_point[0], 3))
                    + "; "
                    + str(round(stuck_point[1], 3))
                )
                graph.add_edge(
                    subgoal_number, subgoals_count, path=subgoal_subgoal_path
                )

                plt.figure(0)
                show_path(
                    subgoal[0],
                    subgoal[1],
                    stuck_point[0],
                    stuck_point[1],
                    subgoal_subgoal_path,
                    "black",
                )
                plt.plot(
                    stuck_point[0],
                    stuck_point[1],
                    marker="o",
                    color="blue",
                    markersize=4,
                )
                if show_subgoals_numbers:
                    plt.text(
                        stuck_point[0],
                        stuck_point[1],
                        str(subgoals_count),
                        color="black",
                        fontsize=11,
                    )
            else:
                print("Can't create subgoal (maximum reached)")

        else:
            print(
                "Subgoal " + str(subgoal_number) +
                " -> subgoal " + str(i) + ": success"
            )
            graph.add_edge(subgoal_number, i, path=subgoal_subgoal_path)
            show_path(
                subgoal[0],
                subgoal[1],
                subgoals[i][0],
                subgoals[i][1],
                subgoal_subgoal_path,
                "black",
            )
            if nx.has_path(graph, "s", "e"):
                return


def main():
    global subgoals_count
    global max_subgoals_reached

    polygons_data = list()

    read_obstacles_data(polygons_data, obstacles_path)

    polygons = create_polygons(polygons_data)

    try:
        multipolygon = unary_union(polygons)
        polygons = list(multipolygon.geoms)
    except:
        pass

    start_time = time.time()
    path, stuck, stuck_reason, terminal_point = gds(
        polygons, start_x, start_y, end_x, end_y
    )

    if stuck:
        graph.add_node("s")
        graph.add_node("e")

        print("Start -> end stuck (" + stuck_reason + ")")
        subgoals.append(terminal_point)
        graph.add_edge("s", subgoals_count, path=path)
        print(
            "Subgoal "
            + str(subgoals_count)
            + " created at: "
            + str(round(terminal_point[0], 3))
            + "; "
            + str(round(terminal_point[1], 3))
        )

        plt.figure(0)
        show_path(start_x, start_y,
                  terminal_point[0], terminal_point[1], path, "black")
        plt.plot(
            terminal_point[0], terminal_point[1], marker="o", color="blue", markersize=4
        )
        if show_subgoals_numbers:
            plt.text(
                terminal_point[0],
                terminal_point[1],
                str(subgoals_count),
                color="black",
                fontsize=11,
            )

        while not nx.has_path(graph, "s", "e"):
            gds_subgoal(polygons, start_x, start_y, end_x, end_y)
            if max_subgoals_reached:
                print("Path not found (max subgoals reached)")
                show_obstacles(polygons)
                plt.plot(start_x, start_y, color="r", marker="o", markersize=4)
                plt.plot(end_x, end_y, color="g", marker="o", markersize=4)
                plt.axis("square")
                if show_plot:
                    plt.show()
                return False, None

        if nx.has_path(graph, "s", "e"):
            path_nodes = nx.shortest_path(graph, "s", "e", method="dijkstra")
            print("Path found: " + str(path_nodes))
            path_graph = nx.path_graph(path_nodes)
            for edge in path_graph.edges():
                path_part = graph.edges[edge[0], edge[1]]["path"]
                show_path(start_x, start_y, end_x, end_y, path_part, "red")

            show_obstacles(polygons)
            plt.plot(start_x, start_y, color="r", marker="o", markersize=4)
            plt.plot(end_x, end_y, color="g", marker="o", markersize=4)
            plt.axis("square")

            if save_plot:
                name = "result_" + str(i + 1)
                plt.savefig(name, dpi=300)

            if show_plot:
                plt.show()

            if show_graph:
                plt.figure(1)
                nx.draw(graph, with_labels=True)
                plt.show()

            end_time = time.time()
            print("Elapsed time: ", end_time - start_time)
            return True, float(end_time - start_time)

    end_time = time.time()
    print("Elapsed time: ", end_time - start_time)

    show_obstacles(polygons)
    show_path(start_x, start_y, end_x, end_y, path, "red")
    plt.plot(start_x, start_y, color="r", marker="o", markersize=4)
    plt.plot(end_x, end_y, color="g", marker="o", markersize=4)
    plt.axis("square")

    if save_plot:
        name = "result_" + str(i + 1)
        plt.savefig(name, dpi=300)

    if show_plot:
        plt.show()
    return True, float(end_time - start_time)


if __name__ == "__main__":
    # random.seed(1)
    plot_size = 100
    step = 0.3
    max_iterations = 20000
    max_subgoals = 15
    launches = 5

    obstacles_path = "test/density_11.json"
    start_x = 0
    start_y = 0
    end_x = 100
    end_y = 100

    time_list = list()
    success_launches = 0

    show_plot = False
    save_plot = False
    show_graph = False
    show_subgoals_numbers = False
    print_points = False

    for i in range(launches):
        print("Launch " + str(i + 1))
        max_subgoals_reached = False
        final_path = list()
        subgoals = list()
        subgoals_count = 0
        graph = nx.Graph()

        path_found, execution_time = main()

        if path_found:
            success_launches += 1
            time_list.append(execution_time)

    print("- " * 20)
    print("Success launches: " + str(success_launches) + "/" + str(launches))
    if success_launches > 0:
        print("Mean time: " + str(sum(time_list) / len(time_list)))
