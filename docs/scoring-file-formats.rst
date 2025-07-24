*******************************************
Scoring File Formats
*******************************************

This page gives a reference to all **scoretility** import file formats.

Common
---------

File Types
^^^^^^^^^^^^^^

The following file types are allowed.

* csv - comma separated value as specified within `RFC 4180 <http://tools.ietf.org/html/rfc4180>`_, with exceptions that line breaks 
  are not permitted within fields

File Contents
^^^^^^^^^^^^^^^^^^^
File contents are the file header for the first row, and the member list with a row for each member. 
The sections defines the permitted column heading names for each file format, and describes the type of data to be found underneath those headings. 

Alternate Headings are given, separated by commas. Note the commas are not part of the alternate headings.

**Notes**:

* required fields are in **bold**
* column order is not specified or implied by the order of fields in this table
* other columns may be present, and are ignored


.. _Members File Format:

Members File Format
--------------------------
Use this file format when importing members using :ref:`Members view`.

+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| Heading                 | Alternate Headings    | Format              | Description                                                             |
+=========================+=======================+=====================+=========================================================================+
| **FamilyName**          | Last                  | Text                | The member's last (or family) name.                                     |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **GivenName**           | First                 | Text                | The member's first (or given) name.                                     |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **Gender**              |                       | F, M, X,            | Gender of the participant, as M for male, F for female, or X for        |
|                         |                       | female, male, or    | non-binary. Case may be upper, lower, or mixed.                         |
|                         |                       | non-binary          |                                                                         |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **DOB**                 | Date of Birth         | yyyy-mm-dd          | The member's date of birth:                                             |
|                         |                       |                     |                                                                         |
|                         |                       |                     | * yyyy - 4 digit year                                                   |
|                         |                       |                     | * m or mm - 1 or 2 digit month                                          |
|                         |                       |                     | * d or dd - 1 or 2 digit day of the month                               |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **RenewalDate** [#ren]_ | Membership Start Date | yyyy-mm-dd          | The date when the member most recently renewed membership for the club. |
|                         |                       |                     |                                                                         |
|                         |                       |                     | * yyyy - 4 digit year                                                   |
|                         |                       |                     | * m or mm - 1 or 2 digit month                                          |
|                         |                       |                     | * d or dd - 1 or 2 digit day of the month                               |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **ExpirationDate**      | Membership End Date   | yyyy-mm-dd          | The membership's expiration date.                                       |
| [#ren]_                 |                       |                     |                                                                         |
|                         |                       |                     | * yyyy - 4 digit year                                                   |
|                         |                       |                     | * m or mm - 1 or 2 digit month                                          |
|                         |                       |                     | * d or dd - 1 or 2 digit day of the month                               |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **City**                |                       | Text                | The member's home city                                                  |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+
| **State**               |                       | Text                | The member's home state (two digit abbreviation)                        |
+-------------------------+-----------------------+---------------------+-------------------------------------------------------------------------+

.. [#ren] **RenewalDate** and **ExpirationDate** allow scoretility to determine member's eligibility to participate in a series on a given race date


.. _Races File Format:

Races File Format
--------------------------
Use this file format when importing races using :ref:`Races view`.

+--------------+------------+---------------------------------------------------------+
| Heading      | Format     | Description                                             |
+==============+============+=========================================================+
| **year**     | yyyy       | Calendar year under which race will be tallied          |
+--------------+------------+---------------------------------------------------------+
| **race**     | Text       | Name of race                                            |
+--------------+------------+---------------------------------------------------------+
| **date**     | yyyy-mm-dd | Date of race                                            |
+--------------+------------+---------------------------------------------------------+
| time1        | hh:mm      | Time of race, hh is 24 hour format.  E.g., 1pm is 13:00 |
+--------------+------------+---------------------------------------------------------+
| **distance** | Number     | Distance of race (miles)                                |
+--------------+------------+---------------------------------------------------------+
| **surface**  | Text       | road, track or trail                                    |
+--------------+------------+---------------------------------------------------------+

.. _Results File Format:

Results File Format
--------------------------
Use this file format when importing results using :ref:`Races view`.

The following file types are allowed.

* text - text files are files which can be viewed in a text editor as columns of data fields

  * columns are defined by the character positions of the heading fields
  * column first character position is the same as the first character position of the heading field
  * column last character position is two characters before the first character position of the next heading field (or at the end of 
    the record for the final column)
  * note this means that the column heading has to be left justified in the column
  * tab characters are permitted -- after a tab character the character position is considered to be at the next n*8 character position 
    boundary, where n is an integer

* csv - comma separated value as specified within RFC 4180, with exceptions that line breaks are not permitted within fields
* xlsx - excel file format
* xls - ancient excel file format

+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+
| Heading        | Alternate Headings        | Format                        | Description                                                                           |
+================+===========================+===============================+=======================================================================================+
| **place**      | pl, gunplace,             | Number                        | Overall place of the result within the race. Note 1st place should be first           |  
|                | overall |_| place         |                               | record, 2nd place second, and so on                                                   |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **firstname**  | first, first |_| name     | Text                          | Given name of the participant                                                         |  
| [#name]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **lastname**   | last, last |_| name       | Text                          | Family name of the participant                                                        |  
| [#name]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **name**       | runner                    | Text                          | Full name of the participant, as Firstname Lastname                                   |  
| [#name]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **gender**     | g, sex, s, male/female    | F, M, or X                    | Gender of the participant, as M for male, F for female, or X for non-binary.          |  
|                |                           |                               | Case may be upper or lower                                                            |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **age**        | ag                        | Number                        | Age in integral years of the participant, on the day of the race                      |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| city           |                           | Text                          | Participant's hometown city, if known                                                 |  
| [#town]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| st             |                           | Text                          | Participant's hometown state, if known -- two character abbreviation for US states    |  
| [#town]_       |                           |                               | or Canadian provinces, or country for other international participants                |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| hometown       |                           | Text                          | Participants hometown City, ST, if known                                              |  
| [#town]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **chiptime**   | time, actual |_| time,    | `Time Format`_                | Net time from crossing of start mat to crossing of finish mat for chip timed races.   |  
|                | nettime                   |                               | See `Time Format`_ for acceptable time formats                                        |  
| [#time]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  
| **guntime**    | time, actual |_| time     | `Time Format`_                | Gross time from start of race until finish.                                           |  
|                |                           |                               | See `Time Format`_ for acceptable time formats                                        |  
| [#time]_       |                           |                               |                                                                                       |  
+----------------+---------------------------+-------------------------------+---------------------------------------------------------------------------------------+  

.. [#name] It is permissable to replace **firstname** and **lastname** with **name**

.. [#town] It is permissable to replace **city** and **st** with **hometown**

.. [#time] **chiptime** or **guntime** must be present

.. non breaking space
.. |_| unicode:: 0xA0
    :trim:


.. _Time Format:

Time Format
-------------------

Time fields should have the precision as defined in USATF Competition Rules Book rule 165. Format of time must be as follows. Fields within 
square brackets [] are optional.

[[hh:]mm:]ss[.ddd]

where:

* hh is hours
* mm is minutes
* ss is seconds
* ddd is fractional seconds