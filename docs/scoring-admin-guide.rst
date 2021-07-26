===========================================
Scoring Admin Guide
===========================================

Introduction
===========================================

This guide describes the concepts of the **scoretility** Scoring Module, and gives guidance on
how to achieve the work flow.

This document describes how to administer **scoretility**, a race results database. **scoretility** gives a club the ability to define various race series, 
which races are in each series, and to collect and tabulate results for races run. When results are tabulated, standings are made available showing 
the current scores for all the athletes included in that series. For more information, see https://scoretility.com/features.

In order to follow these instructions, you must be a :term:`scoring admin` for **scoretility**. If you need admin privileges for **scoretility**, contact 
the FSRC Chief Technology Dude at technology@steeplechasers.org to be added.

License
===========================================

See https://github.com/louking/rrwebapp/blob/master/README.md#license for details on **scoretility** licensing.

Use Cases
===========================================

General
-------------------------------------------

* To do any administration for scoretility results, you need to be logged in. See :ref:`Log In`.
* For best security, the first time you log in, you should change your password. See :ref:`Change Password`.
* Make sure correct club and year are set in header

Beginning of Year Setup
-------------------------------------------
* Create series, most likely :ref:`copy series from previous year`
* Create divisions, most likely :ref:`copy divisions from previous year`
* Create each race
  
  * A few things to note:
  
    * You’ll probably have to ask around for specific dates of races. If you don’t know the date for a race, add “(date TBD)” to the race name
    * Make sure you have the exact specific number of miles listed for each race. This is for age grade calculations and needs to be very precise.
    * For FSRC, there needs to be two races listed for the decathlon 800m – one that is part of the grand prix and equalizer series, and a separate 
      one that is just part of the decathlon series. The one that is part of the decathlon series is open to all runners while the one that is part 
      of the grand prix and equalizer series is members-only. I.e., we don’t want nonmembers to be included in the grand prix and equalizer standings, 
      but we do want them to be included in the decathlon standing.

..
   see https://www.graphviz.org/
   see http://graphs.grevian.org/

.. graphviz::

    digraph records {
        graph [fontname = "helvetica"];
        node [fontname = "helvetica"];
        edge [fontname = "helvetica"];
        "Series view" -> "Divisions view"[label="divisions"];
        "Series view" -> "Series view"[label="create series"];
        "Divisions view" -> "Races view";
        "Divisions view" -> "Divisions view"[label="create divisions"];
        "Series view" -> "Races view"[label="no divisions"];
        "Races view" -> "Races view"[label="create races"];
    }


FSRC Racing Team Management
-------------------------------------------
* At the scoretility Home page, in the upper right corner, set the date to the current year and the club name to the FSRC Racing Team
* If a racing team member has run a race which is not already in scoretility’s database, the race must be added. See :ref:`Add Race`.

  * When updating the “series” the race is in
  
    * Always click All Races
    * If this race is not on the racing team schedule click Other Races

* Once a race is in the scoretility database, results may be added. Often an individual result would be added, e.g., from the 
  FSRC Racing Team Information Submission Form (Responses) sheet. See :ref:`Add Individual Result`.
* Sometimes there are many racing team members who have run a race. In this case it might be easier to import the results file to 
  include all their results. See :ref:`Add Results From File`.

Maryland/DC Grand Prix Management
------------------------------------------
* At the scoretility Home page, in the upper right corner, set the date to the current year and the club name to the Maryland/DC Grand Prix
* Add results from the :ref:`Races view`
* Follow instructions in :ref:`Edit Participants view`:

  * resolve *missed* and *similar* results
  * confirm all results (these should all be green)
  * tabulate

* when tabulating, resolve any unknown clubs using :ref:`Club Affiliations view`

Results Management Flow
=================================

This section shows the basic flow for importing and tabulating the results for a race.

..
   see https://www.graphviz.org/
   see http://graphs.grevian.org/

.. graphviz::

    digraph records {
         graph [fontname = "helvetica"];
         node [fontname = "helvetica"];
         edge [fontname = "helvetica"];
         "Races view" -> "Edit Participants view"[label="import results"];
         "Edit Participants view" -> "Edit Participants view"[label="resolve missing and similar results"];
         "Edit Participants view" -> "Club Affiliations view"[label="unknown clubs"];
         "Club Affiliations view" -> "Edit Participants view"[label="unknown clubs added"];
         "Edit Participants view" -> "Series Race Results view"[label="tabulate"]
     }
 
Detailed Operations
===========================================

.. _Log In:

Log In
-------------------------------------------
Follow these instructions to log in to scoretility.

* Go to the scoretility home page at scoretility.com 
* Click the log in link in the upper right
* Enter email address and password

.. _Change Password:

Change Password
-------------------------------------------
The internet is a dangerous place, and there are constantly people trying to break into the steeplechasers web site and scoretility. 
**Please pick a secure password, with capitals, lower case, numbers and special characters, at least 8 characters.**

* Click on ⛭ near the log out link
* Enter new Password
* Click **Update** 

.. _Add Series:

Add Series
-------------------------------------------

Races must be part of a series to be tabulated. Generally it’s better to add the series before adding the race. Follow these instructions to add a series.

.. _Copy Series from Previous Year:

Copy Series from Previous Year (needs update)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the series for this club have been set up in a prior year, follow these instructions to copy all the series from the previous year. Do this first before adding a new series for the year. 

* Make sure year and club are set correctly in the scoretility header
* Click Series in navigation menu
* Click **Tools ⛭**, then under Copy Series > Copy from Year, Select year to copy from, then click **Copy**

Add Series from Scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the series for this club have never been set up, follow these instructions to add each series.

* Make sure year and club are set correctly in the scoretility header
* Click Series in navigation menu
* Click Add + near the top of the table
* Give the series a name. 
  
  .. note::
    because of some processing later, it is very important that the name is distinct from other series, i.e., the words in one series name 
    cannot be found in another series name
  
* See :ref:`Series view` for detailed description of the :term:`series` attributes

.. _Add Divisions:

Add Divisions
-------------------------------------------
Series optionally use divisions as part of the tabulation process. 


.. _Copy Divisions from Previous Year:

Copy Divisions from Previous Year (needs update)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the divisions for this club have been set up in a prior year, follow these instructions to copy all the divisions from a previous year. 
Do this first before adding new divisions for the series. 

* Make sure year and club are set correctly in the scoretility header
* Make sure series have been set up as in Add Series
* Click Divisions in navigation menu
* Click **Tools ⛭**, then under Copy Divisions > Copy from Year, Select year to copy from, then click **Copy**

Add Divisions from Scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the divisions for this club have never been set up, follow these instructions to add divisions for each series.

* Make sure year and club are set correctly in the scoretility header
* Make sure series have been set up as in Add Series
* Click Divisions in navigation menu
* Click **New** near the top of the table
* Repeat for each age range
  
  * Choose a series 
  * Set age range for this division
  * Click **Create**

  
.. _Add Race:

Add Race
-------------------------------------------
Follow these instructions to add a race.

* Make sure year and club are set correctly in the scoretility header
* Click Races in navigation menu
* Click **New** near the top of the table
* Enter the race name, date, surface and distance. For most accurate age grading, use the following distances for non-integral mile races. 
  (Chief Technology Dude admits to being anal about this)

  * 5K - 3.10686 miles
  * 10K - 6.21371 miles
  * Half marathon - 13.1094 miles
  * Marathon - 26.2188 miles
  
* Click on the “series” the race will be in
* Click **Create**


.. _Edit Results:

Edit Results
-------------------------------------------
The main point of scoretility is to add results to the database and to update series standings through tabulation of these results. Results can be 
added from a file when all the results for a race are added at once, or individually, in cases when only a few results need to be added.

.. _Add Results from File:

Add Results from File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Follow these instructions to add results from a race results file. Import files must follow the format defined 
at :ref:`Results File Format`.

* Make sure year and club are set correctly in the scoretility header
* Click Races in navigation menu
* In the Results column, there will be a button with **import** or **✔**
  
  * Click **import** or **✔**
  * Click Choose File then navigate to the file to be imported
  * Click **Open** 
  * Click **Import** 
  
* If there are already results in the race, you will be asked Overwrite results? 
  
  * This is normally ok because the results from the file are the “official” results
  * Click **Overwrite** 
  
    .. note::
        any results previously entered into the race will be overwritten

* You will be put into the Edit Participants view. See :ref:`Edit Participants view` for details on how to manage the results
  and tabulate for the standings.
  
.. _Add Individual Result:

Add Individual Result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Follow these instructions to add an individual result. Note if you import results from a file later, this individual result will be lost.

* Make sure year and club are set correctly in the scoretility header
* Click Races in navigation menu
* In the Results column, it will either say **import** or **✔**
  
  * Click **import** or **✔**, then click **Edit Participants** to get to :ref:`Edit Participants view`
  
* In the table header, near the left, click **New** 

  * In **Result Name** start typing the name of the member and select, or just select from the pulldown
  * **Age** and **Gender** should automatically be filled in

* Type in the **Time**. See :ref:`Time Format` for the format.
* No need to fill in **Hometown** 
* No need to fill in **Club** unless club is required for the series
* Click **Create** 
* Near top of :ref:`Edit Participants view` next to **Match** filter click **Tools ⛭** 
* Under Tabulate Results, click **Tabulate** (this step updates the standings)
